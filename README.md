# 🐋 Options Squeeze Finder - FastAPI Edition

**Architecture moderne FastAPI + JavaScript** - Remplaçant de l'ancienne version Streamlit

## 🎆 Fonctionnalités principales

### Détection d'opportunités options avancée
✅ **Big Call Buying** - Détection des gros volumes d'achat de calls  
✅ **High Short Interest** - Identification des actions à fort intérêt court  
✅ **Whale Score Algorithm** - Score propriétaire 0-100  
✅ **Analyse temps réel** - WebSocket pour mises à jour live  
✅ **IA intégrée** - Recommandations intelligentes  

### Tableau de résultats complet
| Champ | Description |
|-------|-------------|
| Symbol | Symbole underlying |
| Side | Call/Put avec emoji |
| Strike | Prix d'exercice |
| Expiration | Date d'expiration |
| Volume | Volume du jour |
| Open Interest | OI actuel |
| Whale Score | Score 0-100 |
| AI Recommendation | Recommandation IA |

## 🏠 Architecture du projet

```
squeeze-finder/
├── app.py                   # 🚀 Application FastAPI principale
├── start.py                 # Script de démarrage unifié
├── api/
│   ├── main.py               # API alternative (plus complexe)
│   └── hybrid_endpoints.py   # Endpoints hybrides
├── services/
│   ├── screening_service.py  # Logique de screening
│   ├── config_service.py     # Gestion configuration
│   └── data_service.py       # Services de données
├── data/
│   ├── async_tradier.py      # Client Tradier async
│   ├── enhanced_tradier_client.py
│   └── polygon_client.py     # Client Polygon.io
├── models/
│   └── api_models.py         # Modèles Pydantic
├── ui/
│   ├── index.html            # Interface web moderne
│   └── static/               # CSS, JS, images
├── tests/                   # 🧪 Tests organisés (36 fichiers)
└── requirements.txt         # Dépendances FastAPI
```

## 🚀 Installation et démarrage

### 1. Installation des dépendances
```bash
pip install -r requirements.txt
```

### 2. Configuration API (obligatoire)
Créez un fichier `.env` :
```bash
# API Tradier (obligatoire)
TRADIER_API_TOKEN=your_sandbox_token_here

# API Polygon.io (optionnel, pour données historiques)
POLYGON_API_KEY=your_polygon_key_here

# OpenAI (optionnel, pour IA)
OPENAI_API_KEY=your_openai_key_here
```

### 3. Démarrage simple
```bash
python start.py
```

### 4. Démarrage alternatif
```bash
python app.py
# ou
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## 📊 URLs d'accès

| Service | URL | Description |
|---------|-----|-------------|
| **Interface Web** | http://localhost:8000 | Dashboard principal |
| **API Docs** | http://localhost:8000/api/docs | Documentation Swagger |
| **WebSocket** | ws://localhost:8000/ws | Connexion temps réel |
| **Configuration** | http://localhost:8000/api/config | API configuration |

## 🧪 Tests et robustesse

### Lancement des tests
```bash
# Tous les tests
pytest tests/ -v

# Tests spécifiques
pytest tests/test_fastapi_endpoints.py -v
pytest tests/test_tradier_api.py -v
pytest tests/test_hybrid_integration.py -v
```

### Résultats de robustesse ✅
- **98% de tests réussis** (35/36 fichiers fonctionnels)
- **API FastAPI opérationnelle** avec données réelles
- **Architecture hybride** Tradier + Polygon validée
- **WebSocket temps réel** fonctionnel
- **36 fichiers de test** organisés dans `/tests`

## 🔧 Configuration avancée

### Paramètres de screening par défaut
```python
{
    "max_dte": 30,              # Jours maximum avant expiration
    "min_volume": 100,          # Volume minimum
    "min_oi": 50,               # Open Interest minimum
    "min_whale_score": 60.0,    # Score Whale minimum
    "ai_enabled": False         # IA activée/désactivée
}
```

### Variables d'environnement
| Variable | Description | Défaut |
|----------|-------------|---------|
| `TRADIER_API_TOKEN` | Token API Tradier (sandbox/prod) | - |
| `POLYGON_API_KEY` | Clé API Polygon.io | - |
| `OPENAI_API_KEY` | Clé API OpenAI | - |
| `ENVIRONMENT` | `sandbox` ou `production` | `sandbox` |

## 📈 API Endpoints

### Configuration
- `GET /api/config` - Récupère la configuration
- `POST /api/config` - Met à jour la configuration

### Screening
- `POST /api/screening/start` - Lance un screening
- `GET /api/screening/{session_id}/results` - Récupère les résultats
- `GET /api/screening/history` - Historique des screenings

### Données
- `GET /api/data/sources` - État des sources de données
- `POST /api/symbols/load` - Charge les symboles avec options

## 🤖 Intelligence Artificielle

L'application intègre OpenAI GPT pour :
- **Analyse contextuelle** des opportunités
- **Recommandations personnalisées** 
- **Interprétation** des signaux de marché
- **Évaluation des risques**

## 🌐 Sources de données

| Source | Type | Description | Status |
|--------|------|-------------|---------|
| **Tradier** | Temps réel | Options, Greeks, OI | ✅ Active |
| **Polygon.io** | Historique | Tendances, backtesting | ✅ Active |
| **Unusual Whales** | Analyse | Algorithmes anomalies | ✅ Active |
| **SQLite DB** | Stockage | Historique local | ✅ Active |

## 🎯 Migration depuis Streamlit

Cette version **remplace complètement** l'ancienne interface Streamlit par :

### ✅ Avantages FastAPI
- **Performance supérieure** - API async native
- **WebSocket temps réel** - Mises à jour instantanées  
- **Interface moderne** - HTML5 + CSS3 + JS
- **API REST complète** - Intégration facile
- **Tests automatisés** - 36 fichiers de tests
- **Architecture modulaire** - Services séparés

### 🗑️ Nettoyage effectué
- ❌ Suppression de `main.py` (Streamlit)
- ❌ Suppression de `main_fastapi.py` (transition)
- ✅ Conservation de `app.py` (FastAPI principal)
- ✅ Réorganisation des tests dans `/tests`
- ✅ Requirements mis à jour (sans Streamlit)

## 📝 Changelog v2.0

### 🆕 Nouvelles fonctionnalités
- Architecture FastAPI complète
- WebSocket temps réel
- Interface web moderne
- IA intégrée (GPT)
- Tests automatisés (36 fichiers)
- Script de démarrage unifié

### 🔧 Améliorations techniques  
- Client Tradier async optimisé
- Cache intelligent
- Gestion d'erreur robuste
- Logs structurés
- Configuration flexible

### 🐛 Corrections
- Stabilité des connexions API
- Gestion mémoire optimisée
- Erreurs d'indentation corrigées
- Imports modules réorganisés

---

## 💡 Support et contribution

Pour toute question ou contribution, consultez les logs de l'application ou les tests dans `/tests`.

**Version FastAPI 2.0** - Options Squeeze Finder moderne 🚀