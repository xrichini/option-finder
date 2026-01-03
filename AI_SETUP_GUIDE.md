# 🧠 Guide de Configuration - Options Whale Screener avec IA

Ce guide vous explique comment configurer et utiliser les fonctionnalités d'intelligence artificielle du screener d'options.

## 🎯 Fonctionnalités IA Disponibles

### 📊 OpenAI GPT-4 (Analyse Fondamentale)
- **Analyse fondamentale** des tickers avec activité options inhabituelle
- **Stratégies de portefeuille** basées sur les meilleures opportunités
- **Évaluation des risques** et recommandations d'investissement
- **Analyse contextuelle** des positions institutionnelles

### 🔍 Perplexity AI (Recherche Temps Réel)
- **Analyse de sentiment** basée sur les actualités récentes
- **Détection de catalyseurs** (earnings, upgrades, annonces)
- **Monitoring des réseaux sociaux** (Twitter, Reddit, etc.)
- **Intelligence concurrentielle** et analyse sectorielle

## ⚙️ Configuration des Clés API

### 1. Créer le fichier de configuration
```bash
# Créer le dossier .streamlit s'il n'existe pas
mkdir .streamlit

# Copier le fichier d'exemple
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
```

### 2. Obtenir les clés API

#### OpenAI API Key (Recommandé)
1. Visitez [OpenAI Platform](https://platform.openai.com/api-keys)
2. Créez un compte ou connectez-vous
3. Créez une nouvelle clé API
4. **Coût estimé:** ~$0.02-0.10 per analyse (GPT-4)

#### Perplexity API Key (Recommandé)
1. Visitez [Perplexity AI](https://perplexity.ai/settings/api)
2. Créez un compte Pro ($20/mois)
3. Générez une clé API
4. **Coût:** Inclus dans l'abonnement Pro

### 3. Configurer le fichier secrets.toml
```toml
# .streamlit/secrets.toml
TRADIER_API_KEY = "votre_cle_tradier"
OPENAI_API_KEY = "sk-..." # Votre clé OpenAI
PERPLEXITY_API_KEY = "pplx-..." # Votre clé Perplexity
```

### 4. Alternative: Variables d'Environnement
```bash
# Windows (PowerShell)
$env:OPENAI_API_KEY = "votre_cle_openai"
$env:PERPLEXITY_API_KEY = "votre_cle_perplexity"

# Windows (CMD)
set OPENAI_API_KEY=votre_cle_openai
set PERPLEXITY_API_KEY=votre_cle_perplexity

# Linux/Mac
export OPENAI_API_KEY="votre_cle_openai"
export PERPLEXITY_API_KEY="votre_cle_perplexity"
```

## 🚀 Utilisation du Screener avec IA

### 1. Lancer l'application
```bash
streamlit run main.py
```

### 2. Configuration IA dans la Sidebar
- **Activer l'analyse IA:** Cochez la case "Activer l'analyse AI"
- **Nombre d'analyses:** Ajustez le slider (1-10 options analysées)
- **Afficher détails IA:** Activez pour voir les analyses détaillées
- **Statut des APIs:** Vérifiez que vos clés sont bien configurées

### 3. Workflow de Screening Amélioré

#### Étape 1: Charger les Symboles
1. Cliquez sur "🚀 Charger Symboles"
2. Les symboles avec fort short interest sont chargés automatiquement
3. Le pré-filtrage (market cap, volume) est appliqué

#### Étape 2: Scanner avec IA
1. Choisissez l'onglet (📈 Big Calls ou 📉 Big Puts)
2. Cliquez sur "🔄 Scanner + IA"
3. Le système effectue:
   - Screening classique des options
   - Analyse IA des meilleurs résultats
   - Génération de stratégie de portefeuille

#### Étape 3: Analyser les Résultats
- **Tableau enrichi** avec colonnes IA Summary et badges
- **Graphiques colorés** distinguant les résultats avec/sans IA
- **Stratégie de portefeuille** générée automatiquement
- **Métriques avancées** incluant le nombre d'analyses IA

### 4. Interprétation des Résultats IA

#### 🧠 Badges IA
- **🧠 AI: Strong** - Analyse fondamentale très positive (confiance >80%)
- **🧠 AI: Bullish/Bearish** - Sentiment directionnel fort (score >75%)
- **🧠 AI: Catalyst** - Catalyseurs récents détectés

#### 📊 Analyse Fondamentale
- **Résumé:** Pourquoi les institutions font ce pari
- **Confiance:** Score de 0-100% de la fiabilité de l'analyse
- **Recommandations:** Actions spécifiques suggérées
- **Risques:** Facteurs de risque identifiés

#### 🎭 Analyse de Sentiment
- **Score 0-100:** 50=neutre, >60=haussier, <40=baissier
- **Facteurs haussiers/baissiers** identifiés
- **Sources:** News, réseaux sociaux, analyses

#### 📰 Catalyseurs Détectés
- **Earnings:** Annonces de résultats récentes/prochaines
- **Analyst Actions:** Upgrades/downgrades avec prix cibles
- **Corporate News:** Annonces, partenariats, M&A

## 💡 Conseils d'Utilisation

### Optimisation des Coûts
1. **Limitez le nombre d'analyses IA** (5 par défaut recommandé)
2. **Utilisez le screening classique** pour identifier les meilleurs candidats d'abord
3. **Activez l'IA seulement** pour les positions les plus prometteuses

### Interprétation des Analyses
1. **Combinez tous les signaux:** Whale score + IA + historique
2. **Vérifiez la cohérence:** Sentiment IA vs activité options
3. **Attention aux dates:** Catalyseurs récents vs DTE des options

### Gestion des Erreurs
- **Pas de clés API:** Le système fonctionne en mode classique
- **Erreurs d'API:** Messages d'erreur explicites dans la sidebar
- **Timeouts:** Fallback automatique vers le screening classique

## 🔧 Résolution de Problèmes

### "No symbols loaded"
- Vérifiez votre connexion internet
- Assurez-vous que HighShortInterest.com est accessible
- Essayez de réduire les paramètres de filtrage (market cap, volume)

### "OpenAI API Error"
- Vérifiez que votre clé API est valide et active
- Vérifiez votre solde de crédit OpenAI
- Réduisez le nombre d'analyses simultanées

### "Perplexity API Error"
- Vérifiez que votre abonnement Pro est actif
- Vérifiez les limites de taux d'API
- Attendez quelques minutes entre les analyses

## 📈 Exemples d'Utilisation

### Cas d'Usage 1: Scanner Quotidien
1. Lancer le screener chaque matin
2. Screening avec IA activée (5 analyses)
3. Examiner les stratégies de portefeuille suggérées
4. Approfondir les positions avec badges "🧠 AI: Strong"

### Cas d'Usage 2: Analyse Ciblée
1. Identifier un ticker avec activité options inhabituelle
2. Activer "Afficher détails IA" 
3. Examiner tous les onglets (Fondamental, Sentiment, Catalyseurs)
4. Croiser avec l'analyse technique personnelle

### Cas d'Usage 3: Veille de Catalyseurs
1. Utiliser principalement Perplexity pour les actualités
2. Surveiller les upgrades/downgrades d'analystes
3. Anticiper les réactions de marché sur les options

## 🎯 Prochaines Étapes

Après configuration, vous disposerez d'un système de screening d'options de niveau institutionnel combinant:
- **Détection Unusual Whales** avec analyse historique
- **Intelligence artificielle** pour le contexte et les stratégies  
- **Interface utilisateur** intuitive avec visualisations avancées
- **Gestion des risques** automatisée avec recommandations IA

Le système transforme votre analyse d'options d'un simple screening vers une plateforme d'aide à la décision complète powered by AI.