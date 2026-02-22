# Guide d'analyse des résultats de scan

## Base de données

| Fichier | Statut | Contenu |
|---------|--------|---------|
| `data/options_history.db` | ✅ **Actif** | 4162+ lignes, historique de tous les scans |

La table `option_history` contient : `option_symbol`, `underlying`, `scan_date`, `volume_1d`, `open_interest`, `vol_oi_ratio`, `implied_volatility`, `whale_score`, `strike`, `option_type`.

---

## Ordre de lecture des colonnes — priorités

### 1. `VOL/OI` — signal le plus fort

Ratio volume du jour / open interest. Mesure l'activité *inhabituelle* :

| Valeur | Interprétation |
|--------|---------------|
| > 3x | Notable |
| > 5x | Fort signal directionnel — quelqu'un ouvre une nouvelle position aujourd'hui |
| > 10x | Très inhabituel (ex: AMD PUT 19x, ORCL PUT 23x) |

> Un gros volume sur peu d'OI = nouvelle position ouverte aujourd'hui, pas du roll ou delta hedge.

---

### 2. `SCORE` — tri rapide

Composite de vol, OI, vol/OI, DTE. Utile pour classer rapidement mais ne remplace pas la lecture du contexte.

---

### 3. `IV%` + `IVR` — lire ensemble

- **IV% élevée (> 60%) + côté PUT** → le marché paye cher pour se protéger = stress sur ce titre
- **IV% basse (< 25%)** comme AAPL/NVDA → marché complaisant → un CALL avec gros volume est *plus surprenant*
- **IVR > 70** → IV chère vs historique → favorable pour vendre de l'IV
- **IVR < 30** → IV bon marché → favorable pour acheter de l'IV

---

### 4. `DELTA` — qualifier l'intention du trader

| Delta | Intention probable |
|-------|--------------------|
| 0.10 – 0.30 | Pari spéculatif OTM — coût faible, attend un move violent |
| 0.40 – 0.60 | Pari directionnel calibré — veut de l'exposition |
| > 0.70 | ITM — souvent une couverture ou remplacement d'actions |

---

### 5. `DTE` — urgence du signal

| DTE | Signification |
|-----|--------------|
| 0 – 2d | Mouvement attendu **immédiat** (earnings? news? macro?) |
| 3 – 7d | Horizon court — fort signal si gros volume |
| > 30d | Position de fond — moins spéculatif |

---

### 6. `SIZZLE` / `V5D` — accélération récente

SIZZLE = volume aujourd'hui vs moyenne 5 jours.

- **Sizzle > 200% + score élevé** = accélération récente d'intérêt → signal renforcé

---

## Recette pratique

**Étape 1** — Filtre `≤7d` + trier par `VOL/OI` décroissant

**Étape 2** — Garder les lignes avec :
- VOL/OI > 5x
- DTE ≤ 7
- IV > 50%

**Étape 3** — Vérifier la cohérence :
- PUT + IV élevée + VOL/OI fort = protection / pari baissier urgent
- CALL + IV basse + VOL/OI fort = pari haussier spéculatif (marché complaisant)
- CALL/PUT + delta < 0.25 + DTE ≤ 3 = loterie / catalyseur imminent attendu

**Étape 4** — Vérifier le contexte du titre :
- Earnings dans les 7 jours ?
- Annonce macro (Fed, CPI, NFP) ?
- Mouvement de secteur en cours ?

---

## Exemples de signaux forts (scan 2026-02-22)

| Ticker | Type | VOL/OI | IV% | Lecture |
|--------|------|--------|-----|---------|
| ORCL | PUT | 23x | 92% | Très inhabituel — protection ou pari baissier avec IV chère |
| AMD | PUT | 19x | 77% | Signal fort — quelqu'un se couvre massivement |
| NVDA | PUT | 10x | 26% | Gros volume sur IV basse — inattendu, surveiller |
| AAPL | CALL | 11x | 20% | CALL spéculatif sur IV très basse = pari haussier low-cost |

---

## Colonnes à venir (en cours d'implémentation)

- `IVR` — IV Rank sur 1 an (% entre min et max historique)
- `V5D` — Volume moyen 5 jours (base pour le sizzle)
- `OI Spike` — Variation d'OI par rapport à J-1
