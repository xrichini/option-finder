# Architecture Hybride Tradier + Polygon.io

## 🏗️ Vue d'ensemble

Cette architecture hybride combine le meilleur de deux mondes pour l'analyse d'options :

- **🚀 Tradier** : Source principale pour données options temps réel
- **📊 Polygon.io** : Source complémentaire pour données historiques et tendances

## 🔧 Composants

### 1. HybridDataService
**Fichier :** `services/hybrid_data_service.py`

Service de base qui gère la fusion des données Tradier + Polygon.io :

- ✅ Récupération données temps réel (Tradier)
- ✅ Récupération données historiques (Polygon.io)  
- ✅ Calcul de métriques composites
- ✅ Gestion du cache et rate limiting
- ✅ Fallback gracieux si Polygon.io indisponible

```python
from services.hybrid_data_service import HybridDataService

# Initialisation
hybrid_service = HybridDataService(enable_polygon=True)

# Enrichissement d'une opportunité
hybrid_metrics = await hybrid_service.enrich_opportunity_with_hybrid_data(opportunity)

print(f"Score hybride: {hybrid_metrics.hybrid_score}")
print(f"Tendance 30j: {hybrid_metrics.price_trend_30d}")
```

### 2. HybridScreeningService
**Fichier :** `services/hybrid_screening_service.py`

Service de screening enrichi qui étend le `ScreeningService` existant :

- ✅ Screening classique + enrichissement hybride
- ✅ Scores de confiance basés sur données multiples
- ✅ Recommandations intelligentes avec gestion du risque
- ✅ Analyse des anomalies de volume historique

```python
from services.hybrid_screening_service import HybridScreeningService

hybrid_screening = HybridScreeningService()

# Screening hybride
opportunities = await hybrid_screening.screen_options_hybrid(
    symbols=["AAPL", "TSLA", "SPY"],
    min_whale_score=70.0
)

# Recommandations IA
recommendations = await hybrid_screening.get_hybrid_recommendations(max_results=10)
```

### 3. Endpoints FastAPI
**Fichier :** `api/hybrid_endpoints.py`

Nouveaux endpoints spécialisés pour l'architecture hybride :

## 🌐 API Endpoints

### GET `/api/hybrid/status`
Statut complet de l'architecture hybride

**Response:**
```json
{
  "success": true,
  "timestamp": "2024-01-15T10:30:00Z",
  "status": {
    "hybrid_service": "active",
    "tradier_client": "active", 
    "polygon_client": "active",
    "polygon_enabled": true,
    "cache_entries": 15,
    "architecture": "Tradier (realtime) + Polygon.io (historical)"
  }
}
```

### POST `/api/hybrid/screen`
Screening d'options avec enrichissement hybride

**Request:**
```json
{
  "symbols": ["AAPL", "TSLA", "SPY"],
  "option_type": "both",
  "max_dte": 30,
  "min_volume": 100,
  "min_whale_score": 70.0
}
```

**Response:**
```json
{
  "success": true,
  "results": {
    "opportunities": [
      {
        "option_symbol": "AAPL240315C00185000",
        "hybrid_score": 85.5,
        "realtime_score": 75.0,
        "historical_score": 82.0,
        "volume_anomaly_ratio": 3.2,
        "price_trend_30d": "bullish",
        "volatility_regime": "high",
        "data_freshness": "fresh",
        "polygon_available": true
      }
    ],
    "count": 1
  }
}
```

### GET `/api/hybrid/recommendations`
Recommandations de trading basées sur l'analyse hybride

**Response:**
```json
{
  "success": true,
  "recommendations": [
    {
      "option_symbol": "AAPL240315C00185000",
      "confidence_score": 88.5,
      "recommendation_type": "STRONG_BUY",
      "risk_level": "MEDIUM",
      "target_profit": 132.8,
      "stop_loss": -30.0,
      "historical_context": "Tendance 30j: bullish | Volume 3.2x la moyenne | Volatilité: high"
    }
  ]
}
```

### GET `/api/hybrid/data-sources`
Informations détaillées sur les sources de données

### GET `/api/hybrid/historical/{symbol}?days=30`
Analyse historique détaillée d'un symbole via Polygon.io

## 🎯 Métriques Hybrides

### HybridMetrics
Modèle de données unifié pour les métriques enrichies :

```python
@dataclass
class HybridMetrics:
    # Données temps réel (Tradier)
    current_volume: int
    current_oi: int
    current_price: float
    greeks_quality: str  # "excellent", "good", "poor"
    
    # Données historiques (Polygon.io)
    avg_volume_30d: Optional[float] = None
    volume_anomaly_ratio: Optional[float] = None  # Ratio d'anomalie
    price_trend_30d: Optional[str] = None  # "bullish", "bearish", "neutral"
    volatility_regime: Optional[str] = None  # "low", "normal", "high"
    
    # Scores composites
    realtime_score: float = 0.0      # Score basé sur Tradier
    historical_score: float = 0.0    # Score basé sur Polygon.io
    hybrid_score: float = 0.0        # Score final composite (60% realtime + 40% historical)
```

## 🔄 Algorithme de Scoring Hybride

### Score Temps Réel (Tradier)
- **Volume** (0-40 pts) : Basé sur volume absolu
- **Open Interest** (0-30 pts) : Basé sur OI absolu
- **Ratio Volume/OI** (0-20 pts) : Indicateur d'activité
- **DTE** (0-10 pts) : Bonus pour DTE optimal (3-14 jours)

### Score Historique (Polygon.io)
- **Anomalie Volume Underlying** (0-40 pts) : Volume inhabituel = opportunité
- **Alignement Tendance/Type** (0-30 pts) : Call sur tendance haussière, etc.
- **Régime de Volatilité** (0-30 pts) : Haute volatilité = plus d'opportunités

### Score Composite Final
```
hybrid_score = (realtime_score × 0.6) + (historical_score × 0.4)
```

Si Polygon.io indisponible :
```
hybrid_score = realtime_score  # Fallback gracieux
```

## 🎨 Recommandations IA

### Types de Recommandations
- **STRONG_BUY** : Confiance ≥80% + Score ≥85
- **BUY** : Confiance ≥70% + Score ≥75
- **SPECULATIVE_BUY** : Volume anomaly ≥3x + Confiance ≥60%
- **WATCH** : Confiance ≥50%
- **NEUTRAL** : Autres cas

### Niveaux de Risque
- **HIGH** : DTE ≤7j ou volatilité élevée ou Greeks de mauvaise qualité
- **MEDIUM** : DTE ≤14j ou volatilité normale
- **LOW** : Autres cas

### Objectifs et Stop Loss
- **HIGH risk** : Target = confidence × 2, Stop = -50%
- **MEDIUM risk** : Target = confidence × 1.5, Stop = -30%
- **LOW risk** : Target = confidence × 1.0, Stop = -20%

## 🚀 Utilisation

### 1. Tests d'intégration
```bash
python test_hybrid_integration.py
```

### 2. Lancement de l'API
```bash
python app.py
```

### 3. Documentation interactive
Ouvrir : http://localhost:8000/api/docs

## 📊 Configuration

### Variables d'environnement
```bash
# Obligatoire - Tradier API  
TRADIER_API_TOKEN=your_tradier_token

# Optionnel - Polygon.io (améliore l'analyse)
POLYGON_API_KEY=your_polygon_key

# Si pas de Polygon.io : fallback sur Tradier seul
```

### Configuration dans code
```python
# Activer/désactiver Polygon.io
hybrid_service = HybridDataService(enable_polygon=True)

# Paramètres de cache
cache_ttl = 300  # 5 minutes
```

## 🔧 Architecture Technique

### Flux de données
```
1. Requête screening hybride
2. Screening classique (Tradier) → Opportunités de base
3. Enrichissement historique (Polygon.io) → Métriques étendues
4. Calcul scores composites → Opportunités enrichies
5. Filtrage et tri → Résultats finaux
6. Génération recommandations → Conseils trading
```

### Gestion d'erreurs
- **Polygon.io indisponible** : Fallback sur Tradier seul
- **Rate limiting** : Cache intelligent 5 min
- **Erreurs API** : Logging + continuation du traitement
- **Données partielles** : Marquage explicite dans `data_freshness`

### Performance
- **Cache** : 5 minutes pour données historiques
- **Concurrence** : Traitement asynchrone complet
- **Rate limiting** : Respect des limites Polygon.io (5 req/min free tier)
- **Batch processing** : Optimisation pour multiple symboles

## 📈 Avantages

### Vs Architecture Tradier seule
- ✅ **Contexte historique** : Détection tendances long terme
- ✅ **Anomalies de volume** : Comparaison avec moyennes historiques
- ✅ **Régimes de volatilité** : Identification périodes opportunes
- ✅ **Scores plus précis** : Fusion données temps réel + historique
- ✅ **Recommandations enrichies** : Contexte pour décisions trading

### Vs Polygon.io seul
- ✅ **Données temps réel** : Options Greeks, OI précis
- ✅ **Pas de rate limiting strict** : Screening rapide
- ✅ **Données options complètes** : Chaînes complètes disponibles
- ✅ **Coût** : Tradier gratuit pour options

## 🎯 Cas d'usage

### Trading Court Terme
```python
opportunities = await hybrid_screening.screen_options_hybrid(
    symbols=["SPY", "QQQ", "AAPL"],
    max_dte=7,  # Options très courtes
    min_volume=1000,  # Volume élevé
    min_whale_score=80.0  # Score élevé
)
```

### Analyse Swing Trading
```python
opportunities = await hybrid_screening.screen_options_hybrid(
    symbols=portfolio_symbols,
    max_dte=30,  # Options plus longues
    min_whale_score=60.0  # Score modéré
)
```

### Recommandations Automatiques
```python
recommendations = await hybrid_screening.get_hybrid_recommendations(
    max_results=20
)

strong_buys = [r for r in recommendations if r['recommendation_type'] == 'STRONG_BUY']
```

## 🔮 Évolutions Futures

### Phase 2 : Machine Learning
- Modèles prédictifs basés sur historique
- Classification automatique des patterns
- Optimisation des seuils dynamiques

### Phase 3 : Sources Supplémentaires
- News sentiment analysis
- Options flow institutionnel
- Indicateurs macro-économiques

### Phase 4 : Backtesting
- Validation historique des recommandations
- Métriques de performance tracking
- Optimisation paramètres ML

---

🔗 **Architecture hybride opérationnelle et prête pour production !**