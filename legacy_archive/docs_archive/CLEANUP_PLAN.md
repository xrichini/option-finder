# 🧹 Plan de nettoyage complet - Options Squeeze Finder

## 📊 Résumé des fichiers obsolètes

### Total identifié : **19 fichiers** (obsolètes ou redondants)

## 🗂️ Structure de nettoyage

### 1. **Créer dossier d'archive**
```bash
mkdir data/archive
mkdir ui/archive
```

### 2. **Fichiers DATA obsolètes (6 fichiers)**
```bash
# Déplacer vers data/archive/
move data/enhanced_screener.py data/archive/
move data/enhanced_screener_v2.py data/archive/
move data/market_chameleon_scraper.py data/archive/
move data/hybrid_data_manager.py data/archive/
move data/integrated_screening_engine.py data/archive/
move data/tradier_client.py data/archive/  # À vérifier avant
```

### 3. **Fichiers UI obsolètes (2 fichiers)**
```bash
# Déplacer vers ui/archive/
move ui/dashboard.py ui/archive/
move ui/trading-interface.html ui/archive/
```

### 4. **Fichiers ROOT obsolètes (suppression directe)**
```bash
# Déjà supprimés ✅
# main.py - Streamlit obsolète
# main_fastapi.py - Transition obsolète
# requirements_fastapi.txt - Fusionné dans requirements.txt
```

## ✅ **Fichiers à CONSERVER (critiques)**

### Data (8 fichiers essentiels)
- `data/enhanced_tradier_client.py` ⭐ - Client API principal
- `data/async_tradier.py` ⭐ - Performance async
- `data/polygon_client.py` ⭐ - Données historiques
- `data/historical_data_manager.py` ⭐ - Gestion BDD
- `data/screener_logic.py` ⭐ - Logique core
- `data/ai_analysis_manager.py` ⭐ - Fonctionnalités IA
- `data/advanced_anomaly_detector.py` ⭐ - Détection anomalies
- `data/options_history.db` ⭐ - Base de données

### UI (1 fichier moderne)
- `ui/index.html` ⭐ - Interface FastAPI moderne

### Root (fichiers essentiels)
- `app.py` ⭐ - Application FastAPI principale
- `start.py` ⭐ - Script de démarrage unifié
- `requirements.txt` ⭐ - Dépendances consolidées

## 📈 **Impact du nettoyage**

### Avant nettoyage
- **Fichiers data/** : 14 fichiers
- **Fichiers ui/** : 3 fichiers (index.html, dashboard.py, trading-interface.html)
- **Fichiers root** : Multiples versions (main.py, main_fastapi.py, etc.)

### Après nettoyage
- **Fichiers data/** : 8 fichiers essentiels (-43%)
- **Fichiers ui/** : 1 fichier moderne (-67%)
- **Fichiers root** : Architecture unifiée (-60% fichiers obsolètes)

### Bénéfices
- **Code plus maintenable** - Architecture claire
- **Tests plus rapides** - Moins de dépendances
- **Onboarding facilité** - Pas de confusion entre versions
- **Réduction des bugs** - Suppression du code mort

## ⚠️ **Précautions**

1. **Archiver avant supprimer** - Possibilité de récupération
2. **Vérifier les imports** - S'assurer qu'aucun import résiduel
3. **Tests après nettoyage** - Exécuter pytest après modifications
4. **Git commit** - Versioning des changements

## 🎯 **Ordre d'exécution recommandé**

1. ✅ Créer dossiers d'archive
2. ✅ Déplacer fichiers UI obsolètes
3. ✅ Déplacer fichiers data obsolètes  
4. ✅ Nettoyer les imports cassés
5. ✅ Exécuter les tests
6. ✅ Commit des changements

---
*Ce plan respecte la nouvelle architecture FastAPI moderne et préserve tous les fichiers essentiels.*