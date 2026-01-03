#!/usr/bin/env python3
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
    print("🐋 OPTIONS SQUEEZE FINDER - FastAPI Backend")
    print("=" * 60)
    print("✅ Architecture moderne FastAPI + JavaScript")
    print("🔄 WebSocket temps réel")
    print("📊 API REST complète")
    print("🤖 IA intégrée pour screening")
    print("-" * 60)


def check_dependencies():
    """Vérifie que les dépendances critiques sont installées"""
    try:
        import fastapi
        import uvicorn

        print(f"✅ FastAPI {fastapi.__version__} détecté")
        print(f"✅ Uvicorn {uvicorn.__version__} détecté")
        return True
    except ImportError as e:
        print(f"❌ Dépendance manquante: {e}")
        print("💡 Exécutez: pip install -r requirements.txt")
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
        print("⚠️  Configuration incomplète — " "vérifiez les variables d'environnement")
        print("💡 Créez un fichier .env avec " "TRADIER_API_KEY_PRODUCTION")
        print()
    else:
        env = Config.get_tradier_environment()
        sandbox_status = "sandbox (dev)" if Config.is_sandbox() else "production"
        print("✅ Clé API Tradier configurée " f"(environnement: {sandbox_status})")
        if not Config.is_sandbox():
            print("💡 Pour utiliser sandbox en dev: TRADIER_SANDBOX=true dans .env")

    # Vérification de l'interface utilisateur
    ui_path = Path("ui/index.html")
    if not ui_path.exists():
        print("⚠️  Interface UI non trouvée dans ui/index.html")
        print("💡 L'application démarrera avec l'API uniquement")
        print()

    print("🚀 Démarrage du serveur...")
    print("📊 Interface: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/api/docs")
    print("🔗 WebSocket: ws://localhost:8000/ws")
    print("=" * 60)

    try:
        # Lancement d'uvicorn avec l'app FastAPI
        uvicorn.run(
            "api.main:app",  # Module:variable depuis api/main.py
            host="0.0.0.0",
            port=8000,
            reload=True,  # Auto-reload en développement
            log_level="info",
            # Ajout de headers pour développement
            headers=[("X-FastAPI-App", "Options-Squeeze-Finder")],
        )
    except KeyboardInterrupt:
        print("\n👋 Arrêt de l'application...")
    except Exception:
        logger.exception("Erreur au démarrage de l'application")
        sys.exit(1)


if __name__ == "__main__":
    main()
