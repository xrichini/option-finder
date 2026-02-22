# 📈 Analyse des Capacités Tradier pour Données Historiques d'Options

## 🎯 Objectif
Détecter l'activité inhabituelle d'options en comparant le volume/OI actuel avec les moyennes historiques glissantes.

## 📊 APIs Tradier Disponibles (basé sur documentation)

### 1. **Market Data APIs**
- `/v1/markets/quotes` - Prix actuels avec volume du jour
- `/v1/markets/options/chains` - Chaînes d'options actuelles
- `/v1/markets/history` - **Données historiques pour actions** (pas options)
- `/v1/markets/timesales` - **Time & Sales data** (intraday pour actions)

### 2. **Limitations Identifiées**
❌ **Pas d'API directe** pour historique de volume d'options  
❌ **Pas d'API directe** pour historique d'Open Interest  
❌ **Time & Sales** semble limité aux actions, pas options  

### 3. **Workarounds Possibles**

#### A. **Stockage Local des Données** ⭐ (Recommandé)
```python
# Créer notre propre base historique
daily_scan_data = {
    "AAPL240115C00150000": {
        "date": "2024-01-10",
        "volume": 2500,
        "open_interest": 5000,
        "price": 1.25
    }
}
```

#### B. **Estimation via Données Externes**
- Utiliser yfinance ou autres APIs gratuites
- Moins précis mais mieux que rien

#### C. **Time & Sales Intraday Analysis**
- Accumuler volume intraday pour estimer patterns

## 🛠️ **Solution Hybride Proposée**

### Phase 1 : Base de Données Historique Locale
1. **Chaque scan** → Sauvegarder résultats dans SQLite
2. **Comparer** volume actuel vs moyenne mobile 5/10/20 jours
3. **Alertes** quand volume > 200% de moyenne

### Phase 2 : Intégration APIs Externes (si nécessaire)
1. **yfinance** pour données options (limitées mais gratuites)
2. **Alpha Vantage** options data (quota limité)
3. **Polygon.io** (payant mais complet)

## 📝 **Implémentation Détaillée**

### Structure Base de Données
```sql
CREATE TABLE option_history (
    id INTEGER PRIMARY KEY,
    option_symbol TEXT NOT NULL,
    underlying TEXT NOT NULL,
    scan_date DATE NOT NULL,
    volume_1d INTEGER,
    open_interest INTEGER,
    last_price REAL,
    whale_score REAL,
    UNIQUE(option_symbol, scan_date)
);
```

### Logique de Détection
```python
def calculate_volume_anomaly(current_volume, historical_volumes, lookback_days=10):
    if len(historical_volumes) < 3:
        return 0.0  # Pas assez d'historique
    
    avg_volume = sum(historical_volumes[-lookback_days:]) / min(lookback_days, len(historical_volumes))
    
    if avg_volume == 0:
        return 0.0
    
    volume_ratio = current_volume / avg_volume
    
    # Scoring basé sur écart à la moyenne
    if volume_ratio >= 5.0:      # 500%+ above average
        return 100.0
    elif volume_ratio >= 3.0:    # 300%+ above average  
        return 85.0
    elif volume_ratio >= 2.0:    # 200%+ above average
        return 70.0
    elif volume_ratio >= 1.5:    # 150%+ above average
        return 50.0
    else:
        return max(0, volume_ratio * 30)
```

## 🎯 **Intégration dans Screening Logic**

### 1. **Enhanced Whale Score v3**
```python
def calculate_enhanced_whale_score_v3(option_data, historical_data):
    # Scores existants (Unusual Whales)
    vol_oi_score = calculate_vol_oi_score(volume, oi)
    block_score = calculate_large_block_score(volume)
    
    # Nouveau: Historical anomaly score
    volume_anomaly = calculate_volume_anomaly(
        current_volume=volume,
        historical_volumes=historical_data.get('volumes', [])
    )
    
    oi_anomaly = calculate_oi_anomaly(
        current_oi=oi,
        historical_oi=historical_data.get('open_interests', [])
    )
    
    # Composite score v3
    composite = (
        legacy_score * 0.25 +           # Legacy (25%)
        vol_oi_score * 0.25 +           # Vol/OI current (25%)
        block_score * 0.20 +            # Large blocks (20%)
        volume_anomaly * 0.20 +         # Volume vs history (20%)
        oi_anomaly * 0.10               # OI vs history (10%)
    )
    
    return min(100.0, composite)
```

### 2. **Dashboard Nouvelles Métriques**
- **Volume vs Avg** : "↗️ 245%" ou "➖ 85%"
- **OI Change** : "🔺 +150%" ou "🔻 -25%"  
- **Anomaly Badge** : "🚨 Hot" pour volume > 300% moyenne

## 🚀 **Plan d'Implémentation**

### Étape 1 : Infrastructure Historique
- [ ] Créer module `HistoricalDataManager`
- [ ] Setup SQLite database
- [ ] Interface pour sauvegarder/récupérer données

### Étape 2 : Enhanced Screening
- [ ] Modifier `OptionsScreener` pour utiliser historique
- [ ] Ajouter anomaly scoring
- [ ] Intégrer dans whale score composite

### Étape 3 : Dashboard Enhancements
- [ ] Nouvelles colonnes volume/OI trends
- [ ] Badges pour anomalies détectées
- [ ] Graphiques historiques (optionnel)

## 💰 **Coût vs Bénéfice**

### ✅ **Avantages**
- **Vraie détection d'activité inhabituelle**
- **Réduction des faux positifs** 
- **Scoring plus intelligent et précis**
- **Base historique propriétaire**

### ⚠️ **Défis**
- **Données historiques manquantes** au début
- **Stockage local** à maintenir
- **Performance** avec grande base de données

### 💡 **Solution Minimale Viable**
Commencer avec **7 jours d'historique** et étendre progressivement.

---

## 🎯 **Recommandation**

**START SIMPLE** : Implémenter stockage local avec 7-10 jours d'historique. 
L'API Tradier ne fournit pas d'historique d'options, donc créer notre propre base est la meilleure approche.

**Next Steps** :
1. Créer `HistoricalDataManager` 
2. Modifier screening pour sauvegarder résultats
3. Ajouter comparaisons historiques au whale score
4. Déployer et accumuler données sur 1-2 semaines