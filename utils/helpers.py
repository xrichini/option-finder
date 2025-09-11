# helpers.py
import streamlit as st
from datetime import datetime, timedelta
from typing import List, Dict


def format_large_number(num: int) -> str:
    """Formate les grands nombres avec des suffixes"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    else:
        return str(num)


def calculate_dte(expiration_date: str) -> int:
    """Calcule les days to expiration"""
    try:
        exp_date = datetime.strptime(expiration_date, '%Y-%m-%d').date()
        return (exp_date - datetime.now().date()).days
    except:
        return 0


def format_percentage(value: float) -> str:
    """Formate un pourcentage"""
    return f"{value:.1f}%"


def get_whale_score_emoji(score: float) -> str:
    """Retourne un emoji basé sur le whale score"""
    if score >= 90:
        return "🐋"
    elif score >= 80:
        return "🦈"
    elif score >= 70:
        return "🐟"
    else:
        return "🐠"


def create_alert_message(combo_symbols: List[str], call_results: List, short_data: List[Dict]) -> str:
    """Crée un message d'alerte pour les symboles combo"""
    message = "🚨 **OPPORTUNITÉS COMBO DÉTECTÉES** 🚨\n\n"

    for symbol in combo_symbols:
        # Trouver les données call
        call_data = [r for r in call_results if r.symbol == symbol]
        short_info = next((s for s in short_data if s['symbol'] == symbol), {})

        if call_data:
            best_call = max(call_data, key=lambda x: x.whale_score)
            message += f"**{symbol}**\n"
            message += f"• 🐋 Best Call: ${best_call.strike} {best_call.expiration} (Score: {best_call.whale_score:.0f})\n"
            message += f"• 📊 Short Interest: {short_info.get('short_percent', 0):.1f}%\n"
            message += f"• 📈 Volume: {best_call.volume_1d:,} | OI: {best_call.open_interest:,}\n\n"

    return message


# Installation et utilisation
def create_installation_guide():
    """Guide d'installation pour l'utilisateur"""
    return """
# 🚀 Guide d'Installation - Options Whale Screener

## 1. Prérequis
```bash
python 3.8+
pip install streamlit requests pandas numpy plotly yfinance python-dotenv openai
```

## 2. Configuration
Créez un fichier `.env` dans le dossier du projet :
```
TRADIER_API_KEY=your_tradier_api_key_here
OPENAI_API_KEY=your_openai_key_here  # Optionnel
PERPLEXITY_API_KEY=your_perplexity_key_here  # Optionnel
```

## 3. Structure des fichiers
```
options_screener/
├── main.py                 # Point d'entrée Streamlit
├── dashboard.py            # Interface utilisateur
├── screener_logic.py       # Logique de screening
├── tradier_client.py       # Client API Tradier
├── option_model.py         # Modèles de données
├── config.py              # Configuration
├── helpers.py             # Fonctions utilitaires
├── .env                   # Variables d'environnement
└── requirements.txt       # Dépendances
```

## 4. Lancement
```bash
streamlit run main.py
```

## 5. Configuration Streamlit Cloud
Si vous déployez sur Streamlit Cloud, ajoutez dans les secrets :
```toml
TRADIER_API_KEY = "your_key_here"
OPENAI_API_KEY = "your_openai_key"
PERPLEXITY_API_KEY = "your_perplexity_key"
```

## 6. Utilisation

### Paramètres principaux :
- **DTE Maximum** : Plage d'expiration (défaut 7 jours)
- **Volume minimum** : Filtre volume quotidien (défaut 1000)
- **Open Interest minimum** : Filtre OI (défaut 500)
- **Score Whale minimum** : Seuil de détection (défaut 70)
- **Short Interest minimum** : Seuil short % (défaut 30%)

### Tableau de résultats :
Le screener retourne un tableau avec :
- **Symbol** : Symbole de l'underlying
- **Side** : Type d'option (Call pour l'instant)
- **Strike** : Prix d'exercice
- **Expiration** : Date d'expiration
- **Delta** : Greek Delta
- **Volume (1D)** : Volume du jour
- **Volume (7D)** : Volume 7 jours (estimé)
- **Open Interest** : Open Interest actuel

### Fonctionnalités avancées :
- ✅ **Whale Score** : Algorithme de scoring propriétaire
- ✅ **Short Interest Analysis** : Détection des actions shortées
- ✅ **Combo Alerts** : Alerte si Big Calls + High Short Interest
- ✅ **Graphiques interactifs** : Visualisation des données
- ✅ **Export des données** : Possibilité d'export CSV

## 7. API Tradier - Points importants

### Endpoints utilisés :
- `/v1/markets/options/expirations` : Liste des expirations
- `/v1/markets/options/chains` : Chaînes d'options avec Greeks
- `/v1/markets/quotes` : Cotations en temps réel

### Limites à considérer :
- **Rate limiting** : Tradier a des limites par minute
- **Données historiques** : Volume 7J estimé (API limitée)
- **Sandbox vs Production** : Vérifiez votre environnement

### Authentification :
```python
headers = {
    'Authorization': f'Bearer {api_key}',
    'Accept': 'application/json'
}
```

## 8. Optimisations futures suggérées

### Performance :
- Cache des données avec TTL
- Requêtes asynchrones
- Pagination pour gros volumes

### Fonctionnalités :
- Alertes temps réel
- Backtesting des signaux
- Intégration IA (OpenAI/Perplexity)
- Export vers Excel/PDF
- API REST pour intégrations

### Monitoring :
- Logs structurés
- Métriques de performance
- Alertes d'erreur

## 9. Troubleshooting

### Erreurs communes :
- ❌ **API Key Invalid** : Vérifiez votre clé Tradier
- ❌ **No Data Found** : Marchés fermés ou symboles incorrects
- ❌ **Rate Limited** : Réduisez la fréquence des requêtes
- ❌ **Import Errors** : Vérifiez l'installation des dépendances

### Support :
- Documentation Tradier : https://documentation.tradier.com
- GitHub Issues pour ce projet
- Community Discord (si disponible)
"""


# Performance tips
PERFORMANCE_TIPS = """
🚀 **Tips de Performance pour l'Options Screener**

1. **Optimisation des requêtes API**
   - Groupez les symboles par batch
   - Utilisez le cache pour éviter les requêtes répétées
   - Implémentez un rate limiter

2. **Filtrage intelligent**
   - Filtrez côté client autant que possible
   - Utilisez des seuils réalistes pour éviter trop de données

3. **Gestion mémoire**
   - Limitez le nombre de résultats affichés
   - Implémentez une pagination pour les gros datasets

4. **Interface utilisateur**
   - Utilisez st.cache_data pour les calculs lourds
   - Implémentez un loading state pour les longues opérations
"""
