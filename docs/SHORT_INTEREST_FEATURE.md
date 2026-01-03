# Fonctionnalité Short Interest

## 📋 Vue d'ensemble

Cette fonctionnalité permet de récupérer automatiquement les actions/ETFs avec un fort taux de short interest depuis le site [highshortinterest.com](https://highshortinterest.com), de les filtrer selon différents critères, puis de lancer un screening d'options sur ces symboles pour identifier des opportunités de trading.

## 🏗️ Architecture

### Composants créés/modifiés

1. **`data/short_interest_scraper.py`** - Module de scraping modernisé
2. **`api/short_interest_endpoints.py`** - Endpoints FastAPI RESTful
3. **`api/main.py`** - Intégration des nouveaux endpoints
4. **`test/test_short_interest_integration.py`** - Tests complets
5. **`test_short_interest_manual.py`** - Script de test manuel

## 🔧 Utilisation

### Via l'API REST

#### 1. Récupérer la liste des stocks avec fort short interest
```http
GET /api/short-interest/stocks
```

**Paramètres de requête (optionnels) :**
- `limit` (int) : Limite du nombre de résultats
- `min_market_cap` (float) : Capitalisation minimum en dollars
- `max_market_cap` (float) : Capitalisation maximum en dollars
- `min_short_interest` (float) : % de short interest minimum
- `sectors` (string) : Secteurs filtrés (séparés par virgules)

**Réponse :**
```json
{
  "stocks": [
    {
      "symbol": "AAPL",
      "short_interest_percent": 15.5,
      "market_cap": 3000000000000,
      "sector": "Technology",
      "price": 150.25,
      "volume": 50000000,
      "days_to_cover": 2.5,
      "float": 15000000000,
      "shares_outstanding": 16000000000
    }
  ],
  "total_count": 1,
  "execution_time": 2.34,
  "timestamp": "2024-01-15T10:30:00Z",
  "filters_applied": {...}
}
```

#### 2. Récupérer seulement les symboles
```http
GET /api/short-interest/symbols
```

**Réponse :**
```json
{
  "symbols": ["AAPL", "TSLA", "GME"],
  "count": 3,
  "execution_time": 1.23,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### 3. Lancer un pipeline complet (scraping + screening)
```http
POST /api/short-interest/scan
```

**Corps de la requête :**
```json
{
  "screening_type": "classic",
  "filters": {
    "min_market_cap": 1000000000,
    "sectors": ["Technology", "Healthcare"],
    "min_short_interest": 12.0
  },
  "screening_config": {
    "max_dte": 7,
    "min_volume": 100,
    "min_oi": 50
  }
}
```

**Réponse :**
```json
{
  "short_interest_stocks": [...],
  "screening_results": [
    {
      "symbol": "AAPL",
      "option_type": "CALL",
      "strike": 155.0,
      "expiration": "2024-01-19",
      "whale_score": 85.2,
      "volume": 15000,
      "open_interest": 8000
    }
  ],
  "pipeline_stats": {
    "stocks_found": 25,
    "opportunities_found": 8,
    "execution_time": 45.67,
    "screening_type": "classic"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### 4. Vérifier la santé du service
```http
GET /api/short-interest/health
```

### Via le code legacy (compatibilité Streamlit)

```python
from data.short_interest_scraper import get_high_short_interest_symbols_legacy

# Utilisation simple compatibles avec l'ancien code
symbols = get_high_short_interest_symbols_legacy(
    min_short_interest=10.0,
    max_results=50
)
# Retourne: ['AAPL', 'TSLA', 'GME', ...]
```

## 📊 Fonctionnalités détaillées

### Scraping et enrichissement des données

- **Source** : https://highshortinterest.com
- **Enrichissement** : Données de marché via yfinance
- **Données collectées** :
  - Symbole du ticker
  - % de short interest
  - Capitalisation boursière
  - Secteur d'activité
  - Prix actuel
  - Volume moyen
  - Float et shares outstanding
  - Jours pour couvrir (days to cover)

### Système de filtrage avancé

**Filtres supportés :**
- **Capitalisation** : Min/Max market cap
- **Short Interest** : Pourcentage minimum
- **Secteurs** : Liste de secteurs autorisés
- **Volume** : Volume minimum requis
- **Liquidité** : Filtrage sur float et volume

### Intégration avec le screening d'options

Le pipeline complet permet de :
1. Récupérer les stocks à fort short interest
2. Appliquer les filtres de pré-sélection
3. Lancer le screening d'options (classic ou AI)
4. Retourner les opportunités consolidées

## 🧪 Tests

### Tests automatisés
```bash
# Tests complets avec pytest
pytest test/test_short_interest_integration.py -v

# Test d'un endpoint spécifique
pytest test/test_short_interest_integration.py::TestShortInterestIntegration::test_health_endpoint -v
```

### Test manuel rapide
```bash
# Lancement du script de test manuel
python test_short_interest_manual.py
```

### Test en ligne de commande
```bash
# Démarrage du serveur FastAPI
uvicorn api.main:app --reload --port 8000

# Test des endpoints
curl http://localhost:8000/api/short-interest/health
curl "http://localhost:8000/api/short-interest/stocks?limit=5"
```

## ⚙️ Configuration

### Variables d'environnement
```bash
# Configuration Tradier (si applicable)
TRADIER_API_KEY=your_api_key
TRADIER_BASE_URL=https://sandbox.tradier.com  # ou production

# Configuration scraping
SHORT_INTEREST_REQUEST_DELAY=1.0  # Délai entre requêtes
SHORT_INTEREST_MAX_RETRIES=3      # Nombre de tentatives
```

### Limites et seuils par défaut
- **Limite par défaut** : 100 stocks
- **Délai entre requêtes** : 1 seconde
- **Timeout par requête** : 10 secondes
- **Seuil short interest minimum** : 5%
- **Capitalisation minimum** : 100M $

## 🔄 Workflow d'intégration

Cette fonctionnalité s'intègre parfaitement dans le workflow existant :

1. **Interface Web** → Paramètres de filtrage
2. **Short Interest API** → Récupération des symboles
3. **Services de screening** → Analyse des options
4. **Dashboard** → Affichage des opportunités
5. **WebSocket** → Mises à jour temps réel

## 📈 Performance

**Métriques typiques :**
- Scraping de 100 stocks : ~15-30 secondes
- Enrichissement yfinance : ~5-10 secondes
- Screening 50 symboles : ~60-120 secondes
- Pipeline complet : ~2-3 minutes

**Optimisations :**
- Cache des données de marché (5 minutes)
- Requêtes asynchrones parallèles
- Limitation du rate limiting
- Filtrage précoce pour réduire le volume

## 🚨 Gestion des erreurs

**Erreurs gérées :**
- Échec de connexion au site source
- Timeouts de requêtes réseau
- Données manquantes ou corrompues
- Symboles invalides
- Limitations de rate limiting

**Stratégie de récupération :**
- Retry automatique avec backoff exponentiel
- Fallback sur cache en cas d'échec
- Logs détaillés pour debugging
- Métriques de santé exposées

## 🔮 Évolutions futures

**Améliorations possibles :**
- Support de sources multiples de short interest
- Cache Redis pour les performances
- Notifications en temps réel sur nouveaux symboles
- Intégration avec d'autres métriques (institutional ownership, etc.)
- Dashboard dédié aux métriques short interest
- Export des données vers CSV/Excel

## 📞 Support et debugging

**Logs utiles :**
```bash
# Vérifier les logs du scraper
tail -f logs/short_interest_scraper.log

# Logs API FastAPI
tail -f logs/fastapi.log
```

**Endpoints de debugging :**
- `GET /api/short-interest/health` - État du service
- `GET /api/status` - État global de l'application
- `GET /api/database/stats` - Statistiques base de données

**Points de contrôle :**
1. Connectivité réseau vers highshortinterest.com
2. Configuration des clés API Tradier
3. Disponibilité des services yfinance
4. État du cache et des données temporaires