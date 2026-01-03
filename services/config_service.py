"""
Service de configuration - Logique métier pure
Remplace les dépendances Streamlit par une gestion d'état propre
"""

from typing import Dict, Any
from models.api_models import ConfigResponse, EnvironmentType
from utils.config import Config
import json
import os
from datetime import datetime


class ConfigService:
    """Service de gestion de la configuration sans dépendances UI"""
    
    def __init__(self):
        self.config_file = "config/runtime_config.json"
        self._runtime_config = self._load_runtime_config()
        
        # Configuration par défaut basée sur l'environnement
        self._default_config = self._get_default_config()
    
    def _load_runtime_config(self) -> Dict[str, Any]:
        """Charge la configuration runtime depuis un fichier"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Impossible de charger la config runtime: {e}")
        
        return {}
    
    def _save_runtime_config(self):
        """Sauvegarde la configuration runtime"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self._runtime_config, f, indent=2)
        except Exception as e:
            print(f"Warning: Impossible de sauvegarder la config: {e}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Récupère la configuration par défaut basée sur l'environnement"""
        return {
            "max_dte": Config.DEFAULT_DTE,
            "min_volume": Config.get_min_volume_threshold(),
            "min_oi": Config.get_min_open_interest_threshold(),
            "min_whale_score": Config.get_min_whale_score(),
            "ai_enabled": Config.has_ai_capabilities(),
            "enable_prefiltering": True,
            "min_market_cap": 100_000_000,
            "min_stock_volume": 500_000,
            "last_updated": datetime.now().isoformat()
        }
    
    def get_current_config(self) -> ConfigResponse:
        """Récupère la configuration actuelle complète"""

        # Merge default + runtime config
        current_config = {**self._default_config, **self._runtime_config}

        env_type = (
            EnvironmentType.SANDBOX
            if Config.is_sandbox()
            else EnvironmentType.PRODUCTION
        )
        return ConfigResponse(
            environment=env_type,
            base_url=Config.get_tradier_base_url(),
            is_development=Config.is_sandbox(),
            min_volume_threshold=current_config["min_volume"],
            min_oi_threshold=current_config["min_oi"],
            min_whale_score=current_config["min_whale_score"],
            ai_capabilities=Config.has_ai_capabilities(),
            screening_parameters=Config.get_screening_parameters()
        )
    
    def update_config(self, updates: Dict[str, Any]) -> ConfigResponse:
        """Met à jour la configuration runtime"""

        # Valider les mises à jour
        valid_keys = {
            "max_dte", "min_volume", "min_oi", "min_whale_score",
            "ai_enabled", "enable_prefiltering", "min_market_cap",
            "min_stock_volume"
        }

        filtered_updates = {
            key: value for key, value in updates.items()
            if key in valid_keys
        }

        if filtered_updates:
            # Mise à jour de la config runtime
            self._runtime_config.update(filtered_updates)
            self._runtime_config["last_updated"] = (
                datetime.now().isoformat()
            )

            # Sauvegarde
            self._save_runtime_config()

        return self.get_current_config()
    
    def get_screening_params(self) -> Dict[str, Any]:
        """Récupère les paramètres pour le screening"""
        current_config = {**self._default_config, **self._runtime_config}

        return {
            "max_dte": current_config.get("max_dte", Config.DEFAULT_DTE),
            "min_volume": current_config.get(
                "min_volume", Config.get_min_volume_threshold()
            ),
            "min_oi": current_config.get(
                "min_oi", Config.get_min_open_interest_threshold()
            ),
            "min_whale_score": current_config.get(
                "min_whale_score", Config.get_min_whale_score()
            ),
            "ai_enabled": current_config.get(
                "ai_enabled", Config.has_ai_capabilities()
            )
        }
    
    def get_symbol_loading_params(self) -> Dict[str, Any]:
        """Récupère les paramètres pour le chargement de symboles"""
        current_config = {**self._default_config, **self._runtime_config}

        return {
            "enable_prefiltering": current_config.get(
                "enable_prefiltering", True
            ),
            "min_market_cap": current_config.get(
                "min_market_cap", 100_000_000
            ),
            "min_stock_volume": current_config.get(
                "min_stock_volume", 500_000
            )
        }
    
    def reset_to_defaults(self) -> ConfigResponse:
        """Remet la configuration aux valeurs par défaut"""
        self._runtime_config = {}
        self._save_runtime_config()
        return self.get_current_config()
    
    def get_config_history(self) -> Dict[str, Any]:
        """Récupère l'historique des modifications de config"""
        return {
            "current": self._runtime_config,
            "defaults": self._default_config,
            "environment": Config.get_tradier_environment(),
            "last_updated": self._runtime_config.get("last_updated")
        }
