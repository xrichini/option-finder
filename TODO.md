# TODO — Squeeze Finder

Last commit: `46d90a4` — Insider enrichment via Finviz (97 tickers with recent activity)

---

## 🔥 Priorité haute

- [x] **Insider Trading**
  - ✅ Plan B implémenté: Finviz (finviz-mcp) + finvizfinance.insider API
  - ✅ Coverage: 97 tickers avec activité insider récente (30 jours)
  - ✅ Sentiment: 🟢 bullish / 🔴 bearish / ⚪ neutral
  - ✅ Score boost: 1.05-1.20x pour bullish
  - 📝 Limitation: Couvre surtout small-caps; mega-caps (AAPL, MSFT, etc.) restent neutral (pas d'activité récente sur Finviz)

- [x] **FMP quota 250 req/day**
  - DOW30 = 30 symbols × (1 profile + 1 ratios-ttm) = 60 appels/scan
  - S&P500 = 500 symbols → 1 000 appels → **dépasse le quota**
  - ✅ Implémenté: enrichissement FMP limité aux **top 50 unique symbols** par whale_score
    (Tradier d'abord, FMP seulement sur les meilleures opps → max 100 appels/scan S&P500)
  - ✅ Compteur quota dans `fmp_enrichment._quota` + exposé sur `GET /api/fmp/cache/status`

- [ ] **Colonnes masquables (UI)** — PRIORITÉ BASSE
  - Ajouter un bouton "Columns" pour afficher/masquer des colonnes (Beta, Insider, IVR, V5d…)
  - Sauvegarder préférence dans `localStorage`

---

## 📊 Features nouvelles

- [x] **Score historique visible**
  - ✅ Sparkline SVG 44×14px inline dans la colonne Score (derniers 7 jours de scan)
  - Couleur : vert si tendance haussière, rouge si baissière, gris si flat
  - Endpoint `GET /api/history/sparklines?symbols=...` (batch, SQLite option_history)
  - Cache JS `_sparklineCache` — réutilisé au re-sort/re-filter sans re-fetch
  - Chargé async après scan et après restauration F5

- [ ] **Alertes / Watchlist**
  - Cocher des lignes pour les ajouter à une watchlist persistante
  - Badge rouge si une option watchlistée atteint un nouveau seuil de score

- [x] **Export CSV**
  - ✅ Bouton `↓ CSV` dans la badges-bar (visible uniquement si résultats présents)
  - Exporte le tableau filtré (21 colonnes) au format CSV UTF-8 avec date dans le nom du fichier

- [ ] **Tri multi-colonnes**
  - Actuellement : tri sur une colonne à la fois
  - Ajouter Shift+clic pour tri secondaire

- [x] **Mise à jour auto**
  - ✅ Live refresh des colonnes volatiles toutes les 30s (pas de re-scan)
  - Colonnes rafraîchies : Vol, OI, Vol/OI, Delta, IV%, Chg%, Stk Vol, Moneyness
  - Colonnes statiques conservées : Sector, Beta, Insider, IVR, V5d, Score, Earnings
  - 1 seul appel Tradier `/markets/quotes?greeks=true` groupé (options + underlyings)
  - Indicateur 🔴 LIVE + timestamp "last refreshed" dans la badges-bar
  - Flash bleu sur les cellules modifiées (animation CSS)
  - Auto-start après scan, auto-stop avant nouveau scan

---

## 🛠 Technique / Qualité

- [ ] **Order Flow Signals — Enrichissement du whale_score**
  - [ ] **#1: Block Trade Detection** ⚡ FACILE
    - Volume > seuil + spread normal = potentiel block trade
    - Flag `has_block_trade` si vol > seuil ET vol > 2×avg_vol_30d
    - Source: Tradier (déjà dispo)
  
  - [ ] **#2: Net Flow Indicator** ⚡ FACILE
    - Bid/ask imbalance = direction du flow
    - Si bid_imbalance > threshold = accumulation (bullish)
    - Heuristique simple sur ticks
    - Source: Tradier quotes

  - [ ] **#4: Spread Compression** ⚡ FACILE
    - Spread petit % = meilleure liquidité = institutional activity probable
    - Flag si spread < 2% ET volume élevé
    - Ratio (ask-bid) / mid_price
    - Source: Tradier

  - [ ] **#3: OI Momentum** 📊 MOYEN
    - Changement OI vs jour précédent = intérêt nouveau
    - OI up 30%+ = nouveaux gros positionnements
    - Source: Comparaison avec `options_history.db`

  - [ ] **#5: Put/Call Flow Ratio** 📊 MOYEN
    - Unusual put volume vs calls = hedge buying (bearish flow)
    - Agrégation par underlying
    - Source: Calcul local

- [ ] **Tests sur FMP quota réel**
  - Faire tourner S&P500 complet et mesurer consommation quota FMP
  - Logger le compteur d'appels dans `/api/fmp/cache/status`

- [ ] **Gestion d'erreur UI**
  - Si FMP quota dépassé (429), afficher un bandeau jaune "Enrichissement FMP limité aujourd'hui"
  - Ne pas bloquer le scan principal

- [ ] **Filtres avancés (bandeau supérieur) — audit complet**
  - Revoir le fonctionnement exact : quels filtres sont appliqués côté serveur (scan) vs côté client (post-scan)
  - S'assurer que Min Vol, Min OI, Score ≥, IV% ≥ sont bien passés au backend ET ré-appliqués client-side
  - Vérifier que le bouton 🔄 (re-apply) et "Apply filters" font la même chose
  - Ajouter des filtres manquants éventuels : DTE min, Delta min/max, Vol/OI min

- [ ] **Purge `options_history.db` — options expirées**
  - Supprimer automatiquement les entrées dont `expiration_date < today`
  - Lancer la purge au démarrage du serveur + endpoint `DELETE /api/history/purge`
  - Optionnel : VACUUM après purge pour compresser le fichier SQLite
  - Objectif : éviter que la DB grossisse indéfiniment (actuellement ~1.2 MB)

- [ ] **Valider les calculs historiques côté DB**
  - Une fois assez de données accumulées (≥ 5-7 jours), vérifier :
    - `sizzle_index` : ratio vol_jour / avg_vol_5j — cohérent avec ce qu'on voit sur le marché ?
    - `vol_trend_ratio` : tendency haussière/baissière du volume d'options sur 5j
    - `iv_rank` : percentile IV sur fenêtre glissante — comparer avec des sources externes (Market Chameleon)
    - Score historique vs score temps-réel : les deux convergent-ils sur les mêmes opps ?
  - Créer un petit script `tests/validate_db_metrics.py` qui dumpe les stats et signale les anomalies

- [x] **Cleanup fichiers docs**
  - Beaucoup de fichiers `.md` à la racine (CLEANUP_PLAN, ANALYSIS_SUMMARY, etc.)
  - Les archiver dans `docs/` ou supprimer

- [ ] **Branch → main**
  - `feature/short-interest` est 33 commits ahead d'origin
  - Faire une PR / merge vers `main` quand Insider est résolu

---

## ✅ Fait (récent)

- [x] FMP stable API migration (`/v3/` → `/stable/`)
- [x] Beta column (color-coded: gris < 1.3 / orange ≥ 1.3 / rouge ≥ 2)
- [x] Earnings ⚡ column (7j calendar)
- [x] Ticker search filter dans la badges-bar
- [x] Sector font agrandi
- [x] get_profiles() per-symbol concurrent (batch cassé sur nouvelle API)
- [x] DOW30 universe + Wikipedia fallback
- [x] TTL cache 24h profile/metrics, 4h insider
