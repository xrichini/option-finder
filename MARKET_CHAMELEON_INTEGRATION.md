# Integration Market Chameleon 🦎

## Vue d'ensemble

Cette intégration permet d'enrichir notre screener d'options avec les données de volumes inhabituels de Market Chameleon, une source reconnue pour l'analyse des options.

## Fonctionnalités

### 1. Scraper Market Chameleon (`market_chameleon_scraper.py`)

**Classe `MarketChameleonScraper`:**
- Récupère les données d'options à volumes inhabituels
- Parse les ratios volume/moyenne historique
- Filtre par symboles et seuils de volume
- Gère les formats de données OCC

**Classe `MarketChameleonEnhancer`:**
- Intègre les données MC dans nos résultats existants
- Confirme nos détections avec les données MC
- Ajoute de nouvelles opportunités ratées par notre screener
- Enrichit le whale_score avec validation externe

### 2. Structure des données

```python
@dataclass
class UnusualOptionVolumeData:
    symbol: str
    option_symbol: str
    option_type: str  # 'call' or 'put'
    strike: float
    expiration: str
    volume: int
    avg_volume: int
    volume_ratio: float  # Ratio clé: volume / avg_volume
    open_interest: int
    last_price: float
    dte: int
    timestamp: datetime
```

## Installation

### Dépendances requises:

```bash
pip install requests beautifulsoup4 pandas
```

### Configuration:

Aucune clé API requise - utilise le scraping web public.

## Utilisation

### 1. Test basique

```bash
# Windows
test_market_chameleon.bat

# Python direct
python test_market_chameleon_integration.py
```

### 2. Intégration dans le screener

```python
from data.enhanced_screener import EnhancedOptionsScreener

# Initialiser avec Market Chameleon
screener = EnhancedOptionsScreener(
    enable_ai=True,
    enable_market_chameleon=True
)

# Le screening automatiquement intègre les données MC
results = await screener.screen_with_ai_analysis(
    symbols=['SPY', 'QQQ', 'TSLA'],
    option_type='call',
    enable_ai_for_top_n=5
)

# Vérifier les enrichissements MC
for result in results:
    if hasattr(result, 'mc_confirmed') and result.mc_confirmed:
        print(f"✅ {result.symbol} confirmé par MC (ratio: {result.mc_volume_ratio:.1f}x)")
    if hasattr(result, 'mc_source') and result.mc_source:
        print(f"🆕 {result.symbol} détecté uniquement par MC")
```

### 3. Utilisation standalone

```python
from data.market_chameleon_scraper import MarketChameleonScraper

scraper = MarketChameleonScraper()

# Récupérer toutes les options inhabituelles
all_data = scraper.scrape_unusual_volume_data(limit=100)

# Filtrer par symboles spécifiques
specific_data = scraper.get_unusual_options_for_symbols(
    symbols=['SPY', 'QQQ', 'TSLA'], 
    min_volume_ratio=2.0
)
```

## Avantages de l'intégration

### 1. Validation croisée
- Nos détections confirmées par source externe réputée
- Réduction des faux positifs
- Augmentation de la confiance dans les signaux

### 2. Couverture élargie
- Détection d'options ratées par notre algorithme
- Différentes méthodologies de calcul
- Source de données complémentaire

### 3. Scoring amélioré
- Bonus au whale_score pour confirmations MC
- Prise en compte des ratios de volume MC
- Scoring hybride plus robuste

## Enrichissements apportés aux résultats

### Nouvelles propriétés ajoutées:

```python
result.mc_confirmed = True/False        # Confirmé par Market Chameleon
result.mc_volume_ratio = 3.5           # Ratio volume MC
result.mc_avg_volume = 1250            # Volume moyen historique MC
result.mc_source = True/False          # Provient uniquement de MC
```

### Exemple d'enrichissement:

```
AVANT:
SPY CALL $500 - Whale Score: 75

APRÈS (avec MC):
SPY CALL $500 - Whale Score: 85 ✅ Confirmé MC (ratio: 4.2x)
```

## Métriques et performance

### Ratios de volume typiques:
- **1.0-2.0x**: Volume normal à légèrement élevé
- **2.0-3.0x**: Volume inhabituel significatif
- **3.0-5.0x**: Volume très inhabituel (signal fort)
- **5.0x+**: Volume exceptionnel (signal majeur)

### Seuils recommandés:
- **Screening général**: min_volume_ratio = 1.5
- **Signaux forts**: min_volume_ratio = 2.5
- **Signaux exceptionnels**: min_volume_ratio = 4.0

## Gestion des erreurs

### Problèmes courants:

1. **Structure HTML modifiée**
   - Erreur: "Impossible de trouver le tableau de données"
   - Solution: Mettre à jour les sélecteurs CSS

2. **Blocage anti-bot**
   - Erreur: HTTP 403/429
   - Solution: Ajouter délais, changer User-Agent

3. **Pas de données**
   - Cause: Marchés fermés, filtres trop stricts
   - Solution: Réduire min_volume_ratio, tester avec symboles liquides

## Tests et validation

### Script de test complet:
```bash
python test_market_chameleon_integration.py
```

**Tests inclus:**
1. Scraping basique
2. Filtrage par symboles spécifiques  
3. Intégration avec screener existant
4. Export des données
5. Statistiques et validation

### Métriques de validation:
- Nombre d'enregistrements récupérés
- Taux de confirmation de nos détections
- Nouvelles opportunités identifiées
- Performance et temps de réponse

## Intégration UI Streamlit

### Contrôles ajoutés:
- Checkbox "Utiliser Market Chameleon"
- Affichage du statut MC dans sidebar
- Badges de confirmation MC sur les résultats
- Métriques de validation croisée

### Indicateurs visuels:
- ✅ Options confirmées par MC
- 🆕 Nouvelles détections MC
- 📊 Ratios de volume MC
- ⚠️ Statut de disponibilité MC

## Conformité et éthique

### Respect des conditions d'utilisation:
- Scraping respectueux avec délais
- Pas de surcharge des serveurs
- Usage limité aux besoins légitimes
- Attribution appropriée de la source

### Considérations légales:
- Données publiques uniquement
- Respect du robots.txt
- Pas de contournement de protections
- Usage personnel/recherche

## Roadmap et améliorations

### Version future:
1. **Cache intelligent** - Éviter les requêtes répétitives
2. **API officielle** - Si Market Chameleon propose une API
3. **Données historiques** - Archiver les ratios de volume MC
4. **Alertes temps réel** - Notifications sur nouvelles détections MC
5. **Analyse comparative** - Historique de validation croisée

### Optimisations:
- Parallélisation des requêtes
- Mise en cache des résultats
- Compression des données
- Interface de monitoring

## Support et maintenance

### Logs et debugging:
```python
# Activer logs détaillés
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Mise à jour:
- Surveiller les changements de structure HTML
- Tester régulièrement la connectivité
- Valider la qualité des données récupérées

### Contact:
Pour problèmes ou suggestions concernant l'intégration Market Chameleon.