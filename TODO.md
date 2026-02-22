# TODO — Squeeze Finder

Last commit: `e0f1d2d` — FMP stable API migration + Beta/Sector enrichment

---

## 🔥 Priorité haute

- [ ] **Insider Trading (payant FMP)**
  - `/stable/insider-trading/search` retourne HTTP 402 → plan B
  - Option A: utiliser `SEC EDGAR` Form 4 (gratuit) — `https://efts.sec.gov/LATEST/search-index?q=%22{sym}%22&dateRange=custom&startdt={30j_ago}&forms=4`
  - Option B: `OpenInsider` scraping (https://openinsider.com/screener) — HTML table, facile à parser
  - Signal attendu: 🟢 bullish / 🔴 bearish / 🟡 mixed / ⚪ neutral sur 30j

- [ ] **FMP quota 250 req/day**
  - DOW30 = 30 symbols × (1 profile + 1 ratios-ttm) = 60 appels/scan
  - S&P500 = 500 symbols → 1 000 appels → **dépasse le quota**
  - Solution: limiter l'enrichissement FMP aux **top N résultats** après scan Tradier
    (fetch Tradier en premier, enrichir FMP seulement sur les ~50 meilleures opps)

- [ ] **Colonnes masquables (UI)**
  - Ajouter un bouton "Columns" pour afficher/masquer des colonnes (Beta, Insider, IVR, V5d…)
  - Sauvegarder préférence dans `localStorage`

---

## 📊 Features nouvelles

- [ ] **Score historique visible**
  - Afficher l'évolution du score sur 5j (sparkline mini dans la colonne Score)
  - Données déjà en base SQLite `options_history.db`

- [ ] **Alertes / Watchlist**
  - Cocher des lignes pour les ajouter à une watchlist persistante
  - Badge rouge si une option watchlistée atteint un nouveau seuil de score

- [ ] **Export CSV**
  - Bouton dans la badges-bar : télécharger le tableau filtré en `.csv`
  - 5 lignes de JS, max

- [ ] **Tri multi-colonnes**
  - Actuellement : tri sur une colonne à la fois
  - Ajouter Shift+clic pour tri secondaire

- [ ] **Mise à jour auto**
  - Toggle "Auto-refresh" toutes les N minutes (5/10/15 min)
  - Indicateur de fraîcheur des données (dernière mise à jour horodatée)

---

## 🛠 Technique / Qualité

- [ ] **Tests sur FMP quota réel**
  - Faire tourner S&P500 complet et mesurer consommation quota FMP
  - Logger le compteur d'appels dans `/api/fmp/cache/status`

- [ ] **Gestion d'erreur UI**
  - Si FMP quota dépassé (429), afficher un bandeau jaune "Enrichissement FMP limité aujourd'hui"
  - Ne pas bloquer le scan principal

- [ ] **Cleanup fichiers docs**
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
