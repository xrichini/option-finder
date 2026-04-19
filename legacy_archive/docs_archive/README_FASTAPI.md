# Options Squeeze Finder - Version FastAPI 🎯

Interface web moderne pour le screening d'options avec WebSocket en temps réel.

## 🚀 Migration Streamlit → FastAPI

Cette version remplace l'interface Streamlit par une API REST moderne avec :
- **FastAPI** : API REST haute performance
- **WebSocket** : Mises à jour temps réel
- **Interface HTML/JS** : Interface responsive intégrée
- **Architecture découplée** : Services métier séparés de l'UI

## 📁 Nouvelle Structure

```
squeeze-finder/
├── api/                    # API FastAPI
│   ├── main.py            # Application FastAPI principale
│   └── __init__.py
├── services/              # Services métier (sans UI)
│   ├── config_service.py  # Gestion configuration
│   ├── screening_service.py # Logique de screening
│   └── __init__.py
├── models/
│   └── api_models.py      # Modèles étendus avec Tradier
├── main_fastapi.py        # Script de démarrage
└── requirements_fastapi.txt
```

## 🔧 Installation

1. **Installer les dépendances FastAPI** :
```bash
pip install -r requirements_fastapi.txt
```

2. **Configuration** (identique) :
```bash
# .env
TRADIER_API_KEY=votre_cle_tradier
TRADIER_ENVIRONMENT=sandbox  # ou production
OPENAI_API_KEY=votre_cle_openai  # optionnel
```

## ▶️ Démarrage

```bash
python main_fastapi.py
```

L'application sera disponible sur :
- **Interface web** : http://localhost:8000
- **Documentation API** : http://localhost:8000/docs
- **WebSocket** : ws://localhost:8000/ws

## 🌐 API Endpoints

### Configuration
- `GET /api/config` - Récupère la configuration actuelle
- `PUT /api/config` - Met à jour la configuration

### Screening
- `POST /api/screening/start` - Lance un screening
- `GET /api/opportunities` - Récupère les opportunités actuelles

### Symboles
- `GET /api/symbols/suggestions` - Suggestions de symboles
- `POST /api/symbols/validate` - Validation de symboles

### Statut
- `GET /api/status` - Statut de l'application

## 📊 Interface Web

L'interface intégrée offre :
- **Screening en temps réel** avec barre de progression
- **Résultats dynamiques** via WebSocket
- **Types de screening** : Classique ou avec IA
- **Configuration personnalisable**

## 🔄 WebSocket Events

L'API WebSocket envoie ces types de messages :

```json
// Début de screening
{
  "type": "screening_started",
  "symbols": ["AAPL", "TSLA"],
  "screening_type": "classic"
}

// Progression
{
  "type": "progress",
  "current": 2,
  "total": 4,
  "message": "Analyse NVDA...",
  "percentage": 50.0
}

// Résultats
{
  "type": "screening_completed",
  "data": {
    "opportunities_count": 15,
    "execution_time": 8.2,
    "opportunities": [...]
  }
}
```

## ⚙️ Services

### ConfigService
- Gestion de la configuration sans dépendances UI
- Persistance dans `config/runtime_config.json`
- Paramètres adaptatifs selon l'environnement

### ScreeningService  
- Logique de screening pure
- Support screening classique et IA
- Callbacks pour progression temps réel
- Validation et suggestions de symboles

## 🔍 Screening Types

### Classique
```json
{
  "symbols": ["AAPL", "TSLA"],
  "screening_type": "classic"
}
```

### Avec IA (experimental)
```json
{
  "symbols": ["AAPL", "TSLA"], 
  "screening_type": "ai"
}
```

## 📈 Avantages vs Streamlit

| Aspect | Streamlit | FastAPI |
|--------|-----------|---------|
| Performance | Moyennne | Haute |
| Temps réel | Limité | WebSocket natif |
| API REST | Non | Oui |
| Testabilité | Difficile | Excellente |
| Déploiement | Complexe | Standard |
| Architecture | Couplée | Découplée |

## 🐛 Débogage

### Logs
```bash
# Les logs sont écrits dans squeeze_finder.log
tail -f squeeze_finder.log
```

### Mode développement
Le serveur redémarre automatiquement lors des modifications de code.

### Tests
```bash
pytest tests/  # TODO: Ajouter tests pour services
```

## 🔮 Prochaines étapes

- [ ] **Implémentation IA complète** dans EnhancedTradierClient
- [ ] **Interface web avancée** en fichier statique
- [ ] **Tests unitaires** pour les services
- [ ] **Authentification** optionnelle
- [ ] **Rate limiting** et monitoring
- [ ] **Docker** pour déploiement

## 📚 Migration depuis Streamlit

Pour migrer du code Streamlit existant :

1. **État de session** → **ConfigService**
2. **Widgets Streamlit** → **API endpoints**
3. **st.progress()** → **WebSocket progress**
4. **Callbacks directs** → **Services async**

## 🤝 Contribution

La nouvelle architecture facilite les contributions :
- Services testables indépendamment
- API documentée automatiquement  
- Code découplé et modulaire

---

*Cette version FastAPI maintient toutes les fonctionnalités du screening d'options tout en offrant une architecture moderne et performante.*