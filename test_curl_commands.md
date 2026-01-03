# Test des endpoints FastAPI avec curl

## 1. Démarrer le serveur FastAPI

```powershell
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

## 2. Tester les endpoints avec curl

### A. Status de l'API
```bash
curl "http://127.0.0.1:8000/api/status"
```

### B. Sources de données hybrides
```bash
curl "http://127.0.0.1:8000/api/hybrid/data-sources"
```

### C. Configuration
```bash
curl "http://127.0.0.1:8000/api/config"
```

### D. Test screening AAPL (paramètres permissifs)
```bash
curl -X POST "http://127.0.0.1:8000/api/hybrid/screen?option_type=both&max_dte=30&min_volume=0&min_oi=0&min_whale_score=0&enable_ai=false" \
     -H "Content-Type: application/json" \
     -d '{"symbols": ["AAPL"]}'
```

### E. Documentation automatique (Swagger UI)
Ouvrez dans le navigateur : http://127.0.0.1:8000/docs

## 3. Points clés à vérifier

### Dans la réponse du screening, cherchez :

```json
{
  "opportunities": [
    {
      "symbol": "AAPL250919C00220000",
      "underlying": "AAPL",
      "strike": 220.0,
      "option_type": "call",
      "expiration": "2025-09-19",
      "implied_volatility": 0.23,  // ← C'EST LA VRAIE IV !
      "delta": 0.4521,             // ← GREEKS RÉELS !
      "gamma": 0.0456,
      "theta": -0.1234,
      "vega": 0.7890,
      "rho": 0.0123,
      // ... autres champs
    }
  ]
}
```

## 4. Questions à poser :

1. **Les IV sont-elles présentes ?** 
   - Chercher `"implied_volatility": X` avec X > 0

2. **Les Greeks sont-ils corrects ?**
   - `delta`, `gamma`, `theta`, `vega`, `rho` présents ?

3. **Y a-t-il des valeurs par défaut ?**
   - Si IV = 0.25 (25%) partout → problème
   - Si Greeks = 0 partout → problème

## 5. Alternative avec PowerShell

```powershell
# Status
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/status" -Method GET

# Screening AAPL
$body = @{
    symbols = @("AAPL")
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/hybrid/screen?option_type=both&max_dte=30&min_volume=0&min_oi=0&min_whale_score=0&enable_ai=false" -Method POST -Body $body -ContentType "application/json"
```

## 6. Analyse des résultats

Si les tests montrent :
- ✅ **IV > 0** → L'API backend fonctionne, problème dans l'interface
- ❌ **IV = 0 ou 25%** → Problème dans la chaîne de traitement backend
- ❌ **Pas de données** → Problème de filtres ou de connexion API