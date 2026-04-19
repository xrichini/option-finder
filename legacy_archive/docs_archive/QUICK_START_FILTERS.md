#!/usr/bin/env python3
"""
QUICK START - Real-Time WebSocket + Advanced Filtering
Examples de comment utiliser les nouvelles features
"""

# ==============================================================================
# EXEMPLE 1: JavaScript - Appliquer un preset
# ==============================================================================

"""
// Dans le navigateur (ui/index.html)

// Créer un instance du filter manager
const filterManager = new AdvancedFilterManager();

// Appliquer le preset "Aggressive"
const filtered = await filterManager.applyPreset(
    currentOptions,  // Liste des opportunités
    'aggressive'     // Nom du preset
);

// Résultats filtrés
console.log(`Filtered from ${currentOptions.length} to ${filtered.length}`);

// Rendre les résultats
renderOptions(filtered);
"""

# ==============================================================================
# EXEMPLE 2: JavaScript - Filtres customisés
# ==============================================================================

"""
// Dans le navigateur

const filterManager = new AdvancedFilterManager();

// Construire des filtres custom
const customFilters = {
    min_whale_score: 60,
    min_dte: 7,
    max_dte: 30,
    min_price: 1.0,
    max_price: 5.0,
    min_volume: 100
};

// Appliquer les filtres
const filtered = await filterManager.applyFilters(
    currentOptions,
    customFilters
);

console.log(`${filtered.length} opportunities match your criteria`);
renderOptions(filtered);
"""

# ==============================================================================
# EXEMPLE 3: JavaScript - Tri multi-colonnes
# ==============================================================================

"""
// Dans le navigateur

const filterManager = new AdvancedFilterManager();

// Trier par whale score (descendant)
const sorted = await filterManager.sortOpportunities(
    opportunities,
    'whale_score',  // Field to sort by
    false           // ascending (false = descending)
);

// Trier par volume (ascendant)
const sortedByVolume = await filterManager.sortOpportunities(
    opportunities,
    'volume',
    true  // ascending
);

// Trier par prix (descendant)
const sortedByPrice = await filterManager.sortOpportunities(
    opportunities,
    'price',
    false
);
"""

# ==============================================================================
# EXEMPLE 4: JavaScript - Save/Load filters
# ==============================================================================

"""
// Dans le navigateur

const filterManager = new AdvancedFilterManager();

// Construire vos filtres
const myFilters = {
    min_whale_score: 70,
    max_price: 2.0,
    min_volume: 100,
    min_dte: 1,
    max_dte: 7
};

// Sauvegarder dans le localStorage du navigateur
filterManager.saveFiltersToLocalStorage(myFilters);
console.log('Filters saved!');

// Plus tard... charger les filtres
const loadedFilters = filterManager.loadFiltersFromLocalStorage();
console.log('Loaded filters:', loadedFilters);

// Appliquer les filtres chargés
const filtered = await filterManager.applyFilters(
    currentOptions,
    loadedFilters
);
"""

# ==============================================================================
# EXEMPLE 5: JavaScript - WebSocket Real-Time
# ==============================================================================

"""
// Dans le navigateur

// Créer un WebSocket manager
const wsManager = new WebSocketManager((message) => {
    console.log('Message reçu:', message.type);
    
    if (message.type === 'opportunities') {
        // Nouvelles opportunités en temps réel!
        const opportunities = message.opportunities;
        console.log(`${opportunities.length} nouvelles opportunités`);
        
        // Rendre immédiatement
        currentOptions = opportunities;
        renderOptions(currentOptions);
        
        // Mettre à jour les stats
        const stats = filterManager.getFilterStats(opportunities);
        updateFilterStats(opportunities);
    }
    
    else if (message.type === 'status') {
        console.log('Status:', message.status);
    }
    
    else if (message.type === 'error') {
        console.error('Error:', message.message);
    }
});

// Connecter au WebSocket
wsManager.connect();

// Vérifier la connexion
if (wsManager.isConnected()) {
    console.log('WebSocket connected!');
}

// Plus tard... déconnecter
wsManager.disconnect();
"""

# ==============================================================================
# EXEMPLE 6: API REST - Appliquer un preset
# ==============================================================================

"""
curl -X POST http://localhost:8000/api/filtering/apply-preset?preset_name=aggressive \\
  -H "Content-Type: application/json" \\
  -d '[
    {
      "symbol": "AAPL",
      "whale_score": 75,
      "last_price": 2.5,
      "volume_1d": 100,
      "dte": 7,
      "open_interest": 500,
      "implied_volatility": 30,
      "strike": 150
    },
    ...
  ]'

# Réponse:
{
  "preset_name": "aggressive",
  "original_count": 50,
  "filtered_count": 12,
  "opportunities": [...]
}
"""

# ==============================================================================
# EXEMPLE 7: API REST - Filtres custom + Tri
# ==============================================================================

"""
curl -X POST "http://localhost:8000/api/filtering/filter-and-sort" \\
  -H "Content-Type: application/json" \\
  -d '{
    "opportunities": [...],
    "filters": {
      "min_whale_score": 60,
      "max_price": 5.0,
      "min_volume": 100
    },
    "sort_by": "whale_score",
    "ascending": false
  }'

# Réponse:
{
  "original_count": 50,
  "filtered_count": 15,
  "final_count": 15,
  "sort_field": "whale_score",
  "sort_ascending": false,
  "opportunities": [...]  # Triés par whale_score
}
"""

# ==============================================================================
# EXEMPLE 8: API REST - Lister tous les presets
# ==============================================================================

"""
curl http://localhost:8000/api/filtering/presets

# Réponse:
{
  "balanced": {
    "name": "Balanced",
    "description": "Balanced risk-reward (default)",
    "is_default": true,
    "filters": {
      "min_whale_score": 50.0,
      "max_price": 5.0,
      "min_volume": 75,
      "min_dte": 1,
      "max_dte": 45,
      "min_oi": 50
    }
  },
  "aggressive": {
    "name": "Aggressive",
    "description": "High whale activity, cheap options",
    "is_default": false,
    "filters": {
      "min_whale_score": 70.0,
      "max_price": 2.0,
      "min_volume": 100,
      "min_dte": 1,
      "max_dte": 45
    }
  },
  ...
}
"""

# ==============================================================================
# EXEMPLE 9: Python - Utiliser le service directement
# ==============================================================================

"""
# Dans votre code Python

from services.advanced_filtering_service import advanced_filtering_service
from models.api_models import AdvancedFilters

# Données d'exemple
opportunities = [
    {
        "symbol": "AAPL",
        "whale_score": 75,
        "last_price": 2.5,
        "volume_1d": 100,
        "dte": 7,
        ...
    },
    ...
]

# 1. Appliquer un preset
filtered = advanced_filtering_service.apply_preset(
    opportunities,
    'aggressive'
)
print(f"Filtered to {len(filtered)} opportunities")

# 2. Appliquer des filtres custom
filters = AdvancedFilters(
    min_whale_score=60,
    max_price=3.0,
    min_volume=100
)
filtered = advanced_filtering_service.filter_opportunities(
    opportunities,
    filters
)

# 3. Trier les résultats
sorted_opps = advanced_filtering_service.sort_opportunities(
    filtered,
    sort_by='whale_score',
    ascending=False
)

# 4. Obtenir les stats
stats = advanced_filtering_service.get_filter_stats(sorted_opps)
print(f"Average whale score: {stats['avg_whale_score']}")
print(f"Price range: {stats['price_range']}")
"""

# ==============================================================================
# EXEMPLE 10: Workflow complet
# ==============================================================================

"""
SCENARIO: Vous voulez trouver les 5 meilleures opportunités agressives

1. Utilisateur ouvre l'interface
   ✓ WebSocket connecté (vert)

2. Cliquez "Short Interest → Options"
   ✓ Sélectionnez symboles (AAPL, TSLA, MSFT)
   ✓ Cliquez "Scan"

3. Résultats arrivent EN TEMPS RÉEL via WebSocket
   ✓ Table se remplit automatiquement
   ✓ 50 opportunités chargées

4. Cliquez "Filtres Avancés" pour ouvrir le panel
   ✓ Panel se déroule

5. Cliquez le preset "Aggressive"
   ✓ Résultats filtrés: 50 → 12 opportunités

6. Cliquez "Appliquer les filtres"
   ✓ Résultats mis à jour immédiatement

7. Sort par "Whale Score" (descending)
   ✓ Les meilleures en haut

8. Ajustez le prix max: $2.00
   ✓ Résultats affichés: 12 → 8

9. Cliquez "Enregistrer"
   ✓ Filtres sauvegardés dans le navigateur

10. Demain, quand vous revenez...
    ✓ Cliquez "Charger"
    ✓ Vos filtres sont restaurés!
    ✓ Prêt à scanner à nouveau

═══════════════════════════════════════════════════════════════════════════

STATISTIQUES AFFICHÉES:
- Total: 8 opportunities
- Avg Score: 72.5
- Price Range: $0.50 - $1.95

VOÜ AVEZ RÉDUIT DE 50 → 8 OPPORTUNITÉS (84% DE RÉDUCTION)!

═══════════════════════════════════════════════════════════════════════════
"""

if __name__ == "__main__":
    print("Voir les commentaires pour les exemples d'utilisation!")
