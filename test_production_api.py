#!/usr/bin/env python3
"""
Script de test pour valider l'API Tradier de production
et vérifier la qualité des données Greeks et IV
"""

# Chargement des variables d'environnement
from dotenv import load_dotenv

load_dotenv()

import sys

sys.path.append(".")

from data.enhanced_tradier_client import EnhancedTradierClient
from utils.config import Config
import logging

logger = logging.getLogger(__name__)


def test_production_api():
    """Test de l'API de production avec focus sur les Greeks"""

    print("🧪 Test de l'API Tradier de production")
    print("=" * 50)

    # Vérification de l'environnement
    print(f"🌐 Environnement: {Config.get_tradier_environment()}")
    print(f"🔗 URL de base: {Config.get_tradier_base_url()}")
    print(f"🔑 Clé API configured: {bool(Config.get_tradier_api_key())}")

    # Initialisation du client
    client = EnhancedTradierClient(Config.get_tradier_api_key(), sandbox=False)

    # Test avec des actions populaires
    test_symbols = ["TSLA", "AAPL", "NVDA", "SPY"]

    for symbol in test_symbols:
        print(f"\n🔍 Test avec {symbol}")
        print("-" * 30)

        # 1. Vérification du sous-jacent
        underlying = client.get_underlying_quote(symbol)
        if not underlying:
            print(f"❌ Impossible de récupérer les données pour {symbol}")
            continue

        price = underlying.get("price", 0)
        print(f"💰 Prix actuel: ${price:.2f}")

        # 2. Récupération des expirations
        expirations = client.get_options_expirations(symbol)
        if not expirations:
            print(f"❌ Aucune expiration trouvée pour {symbol}")
            continue

        print(f"📅 Expirations disponibles: {len(expirations)} ({expirations[:3]}...)")

        # 3. Test d'une chaîne d'options proche de l'ATM
        expiration = expirations[0] if expirations else None
        if not expiration:
            continue

        contracts = client.get_options_chains(symbol, expiration)
        if not contracts:
            print(f"❌ Aucun contrat trouvé pour {symbol} {expiration}")
            continue

        print(f"⛓️ Contrats récupérés: {len(contracts)}")

        # 4. Analyse des contrats ATM pour vérifier les Greeks
        atm_contracts = []
        for contract in contracts:
            strike_diff = abs(contract.strike - price)
            if strike_diff <= price * 0.05:  # Dans les 5% de l'ATM
                atm_contracts.append((contract, strike_diff))

        # Tri par proximité à l'ATM
        atm_contracts.sort(key=lambda x: x[1])

        print("\n📊 Analyse des contrats ATM (±5% du prix actuel)")

        for i, (contract, diff) in enumerate(atm_contracts[:6]):  # Top 6 plus proches
            if i >= 6:
                break

            type_symbol = "📞" if contract.option_type == "call" else "📉"

            print(f"\n{type_symbol} {contract.symbol}")
            print(f"  Strike: ${contract.strike:.0f} (diff: {diff/price*100:.1f}%)")
            print(f"  Bid/Ask: ${contract.bid:.2f}/${contract.ask:.2f}")
            print(f"  Volume: {contract.volume:,} | OI: {contract.open_interest:,}")

            # FOCUS: Analyse détaillée des Greeks
            print("  🧮 Greeks:")
            print(f"    Delta: {contract.delta:.4f}")
            print(f"    Gamma: {contract.gamma:.6f}")
            print(f"    Theta: {contract.theta:.6f}")
            print(f"    Vega: {contract.vega:.6f}")
            print(
                f"    IV: {contract.implied_volatility:.4f} ({contract.implied_volatility*100:.1f}%)"
            )

            # Validation des Greeks
            validate_greeks(contract, symbol, price)

        print(f"\n✅ Test terminé pour {symbol}")
        break  # Ne tester qu'un seul symbole pour commencer


def validate_greeks(contract, symbol, underlying_price):
    """Valide la cohérence des Greeks"""
    issues = []

    # Delta validation
    if contract.option_type == "call":
        if contract.delta < 0 or contract.delta > 1:
            issues.append(
                f"Delta call invalide: {contract.delta} (doit être entre 0 et 1)"
            )
    else:  # put
        if contract.delta > 0 or contract.delta < -1:
            issues.append(
                f"Delta put invalide: {contract.delta} (doit être entre -1 et 0)"
            )

    # IV validation
    if contract.implied_volatility <= 0:
        issues.append(f"IV invalide: {contract.implied_volatility} (doit être > 0)")
    elif contract.implied_volatility > 5:  # Plus de 500% d'IV est suspect
        issues.append(
            f"IV suspicieusement élevée: {contract.implied_volatility*100:.1f}%"
        )

    # Gamma validation (toujours positive)
    if contract.gamma < 0:
        issues.append(f"Gamma invalide: {contract.gamma} (doit être >= 0)")

    # Theta validation (généralement négatif pour les options longues)
    if contract.theta > 0:
        issues.append(f"Theta positif inhabituel: {contract.theta}")

    # Vega validation (généralement positive)
    if contract.vega < 0:
        issues.append(f"Vega invalide: {contract.vega} (doit être >= 0)")

    if issues:
        print("  ⚠️ Problèmes détectés:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("  ✅ Greeks cohérents")


if __name__ == "__main__":
    try:
        test_production_api()
    except KeyboardInterrupt:
        print("\n🛑 Test interrompu par l'utilisateur")
    except Exception:
        logger.exception("Erreur durant le test_production_api")
