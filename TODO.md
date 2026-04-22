# TODO — Squeeze Finder

Last commit: `6e0d1dd` — Sparklines, GHA DB persistence, Phase 1-3 signal enrichment

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

## 🎯 Phase d'Amélioration — Signaux Avancés (vs Unusual Whales)

**Goal**: Competitive advantage vs Unusual Whales — add institutional-grade signals

### **Phase 1 (This Week) — Quick Wins**

- [x] **#1: Moneyness Bucket** ✅ DONE
  - ✅ Moneyness classification: ITM / ATM / OTM
  - ✅ Score boost: ATM +5%, slightly OTM +2%, ITM +1%, far OTM -15%
  - ✅ `moneyness_quality` badge: premium/good/low/neutral
  - ✅ UI: Mon$ column with moneyness indicator bar

- [x] **#2: Bid-Ask Spread Aggression** ✅ DONE
  - ✅ `fill_aggression`: aggressive/normal/patient
  - ✅ Score boost: +3% if aggressive (conviction buying)
  - ✅ `aggression_signal` field in enriched output

- [x] **#3: Size Percentile** ✅ DONE
  - ✅ `size_percentile`: 0-100 ranking vs 30-day avg volume
  - ✅ `volume_30d_avg` stored in options_history.db
  - ✅ Score boost: Top 1% +5%, Top 5% +3%, Top 25% +1%
  - ✅ Badge: 🟢🟢 Top 1% / 🟢 Top 5% / 🟡 Top 25%
  - ✅ UI: SIZE% column with badge

### **Phase 2 — Data Integration** ✅ DONE

- [x] **#4: Fill Velocity** ✅ DONE
  - ✅ `fill_velocity`: contracts/minute from options_history.db
  - ✅ high_velocity / normal / low_velocity classification
  - ✅ UI: FILLVEL column with badge

- [x] **#5: IV Crush Risk Score** ✅ DONE
  - ✅ `iv_crush_risk`: current_iv / 52w_avg_iv ratio
  - ✅ `iv_crush_signal`: high_risk / normal / low_risk
  - ✅ `iv_52w_avg` stored in options_history.db
  - ✅ UI: IVCRUSH column with badge

### **Phase 3 — Advanced** ✅ DONE

- [x] **#6: Order Flow Direction** ✅ DONE
  - ✅ `order_flow_strength`: 0-100 (>50 = bullish conviction)
  - ✅ `order_flow_direction`: strong_bullish / bullish / neutral / bearish
  - ✅ Computed from vol/OI trend analysis across 30-day history
  - ✅ UI: ORDFLOW column with badge + sparkline

- [x] **#7: IV Crush Assessment** ✅ DONE
  - ✅ `crush_probability`: 0-100 (IV dispersion + iv_ratio)
  - ✅ `crush_catalyst`: earnings / volatility_event / none
  - ✅ `volatility_smile`: IV std dev across strikes
  - ✅ UI: CRUSHPROB column with badge + sparkline

---

## 🎨 Phase 4 — UI Enhancements (Option 1: Visual + Analytics)

**Goal**: Enhance user experience with trend visualization and earnings context

### **✅ Task 1: Order Flow Sparklines** (20 min) — COMPLETE
- [x] Add 7-day trend chart for order_flow_strength in table
- [x] Chart shows bullish/bearish direction over time
- [x] Location: Inline sparkline in OrdFlow column (36×12px SVG)
- [x] Endpoint: `GET /api/hybrid/trends/order-flow?symbols=...` (batch)
- [x] Color: Green (bullish trend), Red (bearish trend), Gray (flat)
- [x] Backend method: `HistoryService.get_order_flow_trends()`
- [x] UI function: `_makeFlowTrendSparkline()`
- [x] Async fetch + cache: `_flowTrendCache` populated by `_fetchTrendData()`
- [x] Cache reused with re-sort/re-filter (no re-fetch)
- [x] Deployed: Commit `da529ab`
- Status: ✅ Live in production

### **✅ Task 2: Crush Probability Sparklines** (20 min) — COMPLETE
- [x] Add 7-day trend for crush_probability (IV volatility regime)
- [x] Shows when IV compression risk is rising/falling
- [x] Location: Inline sparkline in CrushProb column (36×12px SVG)
- [x] Endpoint: `GET /api/hybrid/trends/crush-probability?symbols=...` (batch)
- [x] Color: Red (high crush risk rising), Green (crush risk falling), Gray (stable)
- [x] Backend method: `HistoryService.get_crush_probability_trends()`
- [x] UI function: `_makeCrushTrendSparkline()`
- [x] Async fetch + cache: `_crushTrendCache` populated by `_fetchTrendData()`
- [x] Dynamic update: `_updateSparklinesBadges()` injects SVGs after data arrives
- [x] Deployed: Commit `da529ab`
- Status: ✅ Live in production

### **Task 3: Earnings Calendar Integration** (30 min)
- New badge column: "Earnings" showing next earnings date
- Data source: FMP `/calendar/earnings` API + local cache
- Display format:
  - 🔔 DATE if earnings within 7 days (red background = critical)
  - 🔔 DATE if earnings within 30 days (yellow background = caution)
  - ⚪ NO EARNINGS if no events found
- Integrate with crush_probability: auto-set crush_catalyst to "earnings" if date matches
- Cache: 60-minute TTL (FMP rate limit friendly)
- Endpoint: `GET /api/earnings/calendar?symbols=...` (batch)

### **Task 4: Enhanced Tooltips** (15 min)
- Order Flow tooltip: "Vol trend: +15% | OI trend: +8% | Strong bullish conviction"
- Crush Prob tooltip: "IV ratio: 1.8x | 52w avg | Earnings Apr 30 | 85% crush risk"
- Size % tooltip: "Current: 2,500 | 30d avg: 1,200 | Percentile: 98th"
- Fill Vel tooltip: "Velocity: 7,200 contracts/min | Exceptional institutional flow"
- Earnings tooltip: "Q1 earnings: Apr 30 | Last 4Q avg move: 3.2%"

### **Task 5: Trend Indicators in Score Cell** (10 min)
- Add ↗️ (rising), ↘️ (falling), → (flat) symbols next to score
- Indicate 7-day score trend direction
- Color: Green if rising, Red if falling
- Example: "45.2 ↗️" means score improving over week

### **Task 6: Side Panel: Whale Analysis Dashboard** (Optional Enhancement)
- Click on row → slide out panel showing:
  - 30-day order flow history (larger chart)
  - 30-day crush probability history
  - Earnings dates for next 90 days
  - Insider activity (if available)
  - Score composition breakdown (all multipliers)

---

## 🛠 Technique / Qualité

- [ ] **Order Flow Signals — Enrichissement du whale_score**
  - [x] **#1: Block Trade Detection** ⚡ DONE
    - Volume >= 100 contracts detected as potential block trade
    - +3 bonus points to whale_score
    - Source: Tradier volume data

  - [x] **#2: Net Flow Indicator** ⚡ DONE
    - Last price vs bid/ask determines flow direction
    - Closer to ask = buying pressure (bullish)
    - Closer to bid = selling pressure (bearish)
    - +2 bonus if directional signal present
    - Source: Tradier quotes in real-time

  - [x] **#4: Spread Compression** ⚡ DONE
    - Tight spread = institutional liquidity likely
    - Spread < 0.5% = +5 points (very likely whale)
    - Spread < 1% = +3.5 points
    - Spread < 2% = +2 points
    - Source: Tradier bid/ask spreads
    - Impact: +7.4 score differential for institutional options

  - [x] **#3: OI Momentum** ✅ DONE
    - OI change vs day before = new positioning detection
    - OI up 30%+ = +3 bonus points
    - OI up 15-30% = +1 bonus point
    - OI down 20%+ = -2 bonus points
    - Source: Compare with `options_history.db` daily snapshots
    - Appliqué à whale_score après enrichissement historique

  - [x] **#5: Put/Call Flow Ratio** ✅ DONE
    - Unusual put volume vs calls = defensive/hedge buying
    - Put/Call ratio > 1.5 = Defensive (-1 for calls, +1.5 for puts)
    - Put/Call ratio < 0.67 = Call accumulation (+2 for calls, -1 for puts)
    - Source: Aggregate put/call volumes per underlying in scan results
    - Appliqué à whale_score pour détecter patterns de hedging

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

- [x] **Multi-Universe Parallel Scanning** — GHA matrix job (nasdaq100, sp500, dow30 in parallel)
  - 3 parallel jobs execute independently every 15 minutes
  - Each outputs to `data/scan_*.json` with universe field
  - Merge job combines + deduplicates to `data/latest_scan.json` (~630 opps/day)
  - UI universe filter for client-side filtering (no re-scan needed)
  - Rate limiting safe: 630 API calls spread over 5 min (vs 120 limit)
  - History DB enriched 7x: From ~100 opps/day to ~630

- [x] **Put/Call Flow Ratio** — Detects hedging/accumulation patterns (+2 bonus for call accumulation, -1 for defensive puts)
- [x] **OI Momentum** — Flags new positions (+3 for OI +30%, -2 for -20%)
- [x] History DB integration with scan_daemon.py (options_history.db now populated by GHA)
- [x] **GHA DB persistence fix** — options_history.db now committed after every scan (sparklines accumulate)
- [x] **DB seeded** — 4508 historical records (Sep 2025 → Apr 2026) pushed to GitHub
- [x] **Sparkline bugs fixed** — query by `underlying`, 30-day window, single-point dot rendering
- [x] **Column alignment fixed** — removed `display:flex` from `<td>`, moved to `<span>`
- [x] **Phase 1-3 enrichment verified** — size_pct, fill_vel, order_flow, crush_prob all 88/88 in local scan
- [x] GHA workflow fix: deploy now triggers reliably after scan via workflow_run
- [x] FMP stable API migration (`/v3/` → `/stable/`)
- [x] Beta column (color-coded: gris < 1.3 / orange ≥ 1.3 / rouge ≥ 2)
- [x] Earnings ⚡ column (7j calendar)
- [x] Ticker search filter dans la badges-bar
- [x] Sector font agrandi
- [x] get_profiles() per-symbol concurrent (batch cassé sur nouvelle API)
- [x] DOW30 universe + Wikipedia fallback
- [x] TTL cache 24h profile/metrics, 4h insider
