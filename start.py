#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 Script de démarrage Options Squeeze Finder
Version FastAPI moderne - Remplace l'ancienne interface Streamlit
"""

import os
import sys
import uvicorn
from pathlib import Path
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Charger les variables d'environnement dès le démarrage
load_dotenv()


def print_banner():
    """Affiche la bannière de démarrage"""
    print("=" * 60)
    print("OPTIONS SQUEEZE FINDER - FastAPI Backend")
    print("=" * 60)
    print("OK Architecture moderne FastAPI + JavaScript")
    print("LIVE WebSocket temps réel")
    print("STATS API REST complète")
    print("AI IA intégrée pour screening")
    print("-" * 60)


def check_dependencies():
    """Vérifie que les dépendances critiques sont installées"""
    try:
        import fastapi
        import uvicorn

        print(f"OK FastAPI {fastapi.__version__} détecté")
        print(f"OK Uvicorn {uvicorn.__version__} détecté")
        return True
    except ImportError as e:
        print(f"ERROR Dépendance manquante: {e}")
        print("TIP Exécutez: pip install -r requirements.txt")
        return False


def main():
    """Point d'entrée principal"""
    print_banner()

    # Vérification des dépendances
    if not check_dependencies():
        sys.exit(1)

    # Vérification de la configuration Tradier
    from utils.config import Config

    # Valider la config au démarrage. Pour forcer l'application à échouer
    # si des clés manquent, exportez CONFIG_STRICT=true dans l'environnement.
    strict_mode = os.getenv("CONFIG_STRICT", "false").lower() == "true"
    ok = Config.validate(strict=strict_mode)

    if not ok:
        print(
            "WARNING Configuration incomplète — vérifiez les variables d'environnement"
        )
        print("TIP Créez un fichier .env avec TRADIER_API_KEY_PRODUCTION")
        print()
    else:
        env = Config.get_tradier_environment()
        sandbox_status = "sandbox (dev)" if Config.is_sandbox() else "production"
        print(f"OK Clé API Tradier configurée (environnement: {sandbox_status})")
        if not Config.is_sandbox():
            print("TIP Pour utiliser sandbox en dev: TRADIER_SANDBOX=true dans .env")

    # Vérification des autres clés API
    print("\nCHECK Vérification des autres services API:")

    polygon_key = Config.get_polygon_api_key()
    if polygon_key and not polygon_key.startswith("your-"):
        # Valider la clé Polygon en faisant un appel de test
        try:
            from data.polygon_client import PolygonClient
            test_client = PolygonClient(polygon_key)
            if test_client.validate_key():
                print("OK Polygon.io: Configuré et valide")
            else:
                print("WARNING Polygon.io: Clé invalide (données historiques désactivées)")
        except Exception as e:
            print(f"WARNING Polygon.io: Erreur de validation ({str(e)[:50]}...)")
    else:
        print("WARNING Polygon.io: Non configuré (données historiques indisponibles)")
        print(
            "TIP Ajoutez POLYGON_API_KEY dans .env pour activer les données historiques"
        )

    openai_key = Config.get_openai_api_key()
    perplexity_key = Config.get_perplexity_api_key()
    if openai_key and not openai_key.startswith("your-"):
        print("OK OpenAI: Configuré")
    elif perplexity_key and not perplexity_key.startswith("your-"):
        print("OK Perplexity: Configuré")
    else:
        print("WARNING IA (OpenAI/Perplexity): Non configurée (analyse IA désactivée)")
        print(
            "TIP Ajoutez OPENAI_API_KEY ou PERPLEXITY_API_KEY dans .env pour activer l'IA"
        )

    print()
    ui_path = Path("ui/index.html")
    if not ui_path.exists():
        print("WARNING Interface UI non trouvée dans ui/index.html")
        print("TIP L'application démarrera avec l'API uniquement")
        print()

    print("START Démarrage du serveur...")

    # Déterminer le port (par défaut 8001, ou du .env ou argument)
    port = int(os.getenv("PORT", "8001"))
    host = "127.0.0.1"

    print(f"INTERFACE http://localhost:{port}")
    print(f"DOCS http://localhost:{port}/api/docs")
    print(f"WEBSOCKET ws://localhost:{port}/ws")
    print("=" * 60)

    try:
        # Lancement d'uvicorn avec l'app FastAPI
        uvicorn.run(
            "api.main:app",  # Module:variable depuis api/main.py
            host=host,
            port=port,
            reload=True,  # Auto-reload en développement
            log_level="info",
        )
    except KeyboardInterrupt:
        print("\nBYE Arrêt de l'application...")
    except Exception:
        logger.exception("Erreur au démarrage de l'application")
        sys.exit(1)


if __name__ == "__main__":
    main()
