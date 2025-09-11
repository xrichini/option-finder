"""
# Options Screener MVP - Version Finale
# Détection de Big Call Buying et High Short Interest
# Tableau: Symbol, Side, Strike, Expiration, Delta, Volume (day + 7-day), Open Interest
"""

"""
Structure du projet:
options_screener/
├── main.py              # Application Streamlit principale
├── data/
│   ├── tradier_client.py    # Client API Tradier
│   ├── data_processor.py    # Traitement des données
│   └── screener_logic.py    # Logique de screening
├── ui/
│   ├── dashboard.py         # Dashboard principal
│   └── components.py        # Composants UI
├── models/
│   ├── option_model.py     # Modèles de données
│   └── screener_model.py   # Modèles de screening
├── utils/
│   ├── config.py           # Configuration
│   └── helpers.py          # Fonctions utilitaires
└── requirements.txt
"""

🎯 Fonctionnalités principales implémentées :
Tableau de résultats exact :

✅ Symbol : Symbole underlying
✅ Side : Call (comme demandé)
✅ Strike : Prix d'exercice
✅ Expiration : Date d'expiration
✅ Delta : Greek Delta de l'option
✅ Volume (1D) : Volume du jour
✅ Volume (7D) : Volume 7 jours (estimé pour MVP)
✅ Open Interest : Open Interest actuel

Paramètres configurables :

✅ DTE Maximum : Configurable (défaut 7 jours)
✅ Short Interest minimum : Configurable (défaut 30%)
✅ Volume minimum, Open Interest minimum, Score Whale

Fonctionnalités avancées :

🐋 Whale Score Algorithm : Score propriétaire 0-100
🚨 Combo Alerts : Big Calls + High Short Interest
📊 Graphiques interactifs avec Plotly
🎨 Interface moderne avec Streamlit
