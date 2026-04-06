# Plan : Migration VM → GitHub Actions + GitHub Pages

## Contexte

Scanner d'options (unusual flow) actuellement hébergé sur une VM Linux.  
Objectif : supprimer le serveur, pousser sur GitHub, scanner via GHA cron, lire l'UI depuis n'importe quel device via GitHub Pages.

## Décisions

| Décision | Choix |
|---|---|
| Visibilité repo | **Public** (secrets GHA protégés, code visible) |
| Historique (IV Rank, Sizzle Index) | **Exclu de la v1**, prévu en v2 |
| Fréquence de scan | **Toutes les 30 min, lun-ven, heures de marché** |
| Univers v1 | **nasdaq100** (extensible via `workflow_dispatch` input) |
| UI | **Viewer statique** — plus de scan à la demande, plus de WebSocket |

## Architecture cible

```
GitHub Actions (cron */30 14-21 * * 1-5 UTC ≈ 9h30–16h ET)
  └── scan_daemon.py --once --universe nasdaq100
        ├── écrit data/latest_scan.json
        └── git commit + push → main (si données nouvelles)

GitHub Pages (branch gh-pages, auto-déployée)
  ├── index.html + *.js + *.css   ← copiés depuis ui/
  └── data/latest_scan.json       ← copié depuis main

Browser (smartphone / autre PC / tablette)
  └── https://{user}.github.io/squeeze-finder/
        └── fetch('./data/latest_scan.json')
              └── filtrage client-side + affichage
```

---

## Phase 1 — Fix `scan_daemon.py` (market hours en mode `--once`)

**Fichier :** `scan_daemon.py`

**Problème :** `--once` ignore actuellement `is_market_open()` et scanne toujours,
même quand GHA tourne hors des heures de marché.

**Changement :** si `--once` + marché fermé + pas `--force` → `sys.exit(0)` proprement.
Évite ~50 appels API Tradier/FMP inutiles sur chaque run GHA hors marché.

---

## Phase 2 — `.github/workflows/scan.yml`

Nouveau fichier. Déclenché par :
- `schedule` : cron `*/30 14-21 * * 1-5` (UTC = 14h00–21h30, couvre 9h30–16h ET)
- `workflow_dispatch` : test manuel + input `universe` optionnel

Steps :
1. `actions/checkout@v4` avec `fetch-depth: 0` (nécessaire pour le push)
2. `actions/setup-python@v5` Python 3.11 + cache pip
3. `pip install -r requirements.txt`
4. `python scan_daemon.py --once --universe ${{ inputs.universe || 'nasdaq100' }}`
5. Commit + push `data/latest_scan.json` si modifié (bot commit via `GITHUB_TOKEN`)

Secrets requis : `TRADIER_API_KEY_PRODUCTION`, `FMP_API_KEY`, `POLYGON_API_KEY`

---

## Phase 3 — `.github/workflows/deploy.yml`

Nouveau fichier. Déclenché par :
- Push sur `main` avec changement dans `data/latest_scan.json` ou `ui/**`
- `workflow_dispatch`

Steps :
1. `actions/checkout@v4`
2. Préparer `dist/` : copier `ui/*` + `data/latest_scan.json` dans `dist/data/`
3. `JamesIves/github-pages-deploy-action@v4` → branch `gh-pages`

Les deux workflows se coordonnent : `scan.yml` push `main` → déclenche `deploy.yml`.

---

## Phase 4 — Adaptation UI

### `ui/index.html` — suppressions

- `loadConfigFromAPI()` → stub vide
- Calls `GET /api/universe/{id}` et `GET /api/short-interest/symbols` → supprimer
- `POST /api/hybrid/scan-all` + barre de progression + polling `/api/hybrid/scan-progress` → supprimer
- `GET /api/hybrid/scan-result` → supprimer
- `POST /api/quotes/refresh` (mode Live) → supprimer
- `GET /api/history/sparklines` → supprimer (pas d'historique v1)

### `ui/index.html` — ajouts

- `loadLatestScan()` : `fetch('./data/latest_scan.json')` → passe les opportunités au renderer existant (même format `OptionsOpportunity`)
- Bouton **"Rafraîchir"** → appelle `loadLatestScan()`
- Badge **"Mis à jour il y a X min"** calculé depuis `json.timestamp`
- Message d'avertissement si JSON absent ou âge > 2h
- `loadLatestScan()` appelé au `DOMContentLoaded`

### `ui/advanced-filters.js` — suppressions & remplacement

- `GET /api/filtering/presets` → hardcoder les 6 presets localement
- `POST /api/filtering/apply`, `/apply-preset`, `/sort` → `applyFiltersLocally()` sur tableau en mémoire
- `WebSocketManager` et connexion `ws://` → supprimer

---

## Phase 5 — GitHub Pages setup (1 clic)

1. Repository → **Settings** → **Pages**
2. Source : **Deploy from a branch** → branch `gh-pages` → dossier `/`
3. URL finale : `https://{user}.github.io/squeeze-finder/`

---

## Phase 6 — Secrets & validation

1. Repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret** :
   - `TRADIER_API_KEY_PRODUCTION`
   - `FMP_API_KEY`
   - `POLYGON_API_KEY` (optionnel)

2. Onglet **Actions** → `Option Scan (GHA)` → **Run workflow** (test manuel)
3. Vérifier `data/latest_scan.json` committé dans `main`
4. Vérifier UI accessible sur l'URL GitHub Pages
5. Tester filtres client-side
6. Tester sur mobile

---

## Récapitulatif fichiers

| Fichier | Action |
|---|---|
| `scan_daemon.py` | Modifié — exit 0 si marché fermé en mode `--once` |
| `ui/index.html` | Modifié — retirer scan on-demand, ajouter fetch JSON |
| `ui/advanced-filters.js` | Modifié — filtrage client-side, retirer WebSocket |
| `.github/workflows/scan.yml` | Nouveau |
| `.github/workflows/deploy.yml` | Nouveau |
| `docs/plan.md` | Nouveau (ce fichier) |

> Tout le reste (FastAPI, services, api/) n'est pas modifié — la VM reste fonctionnelle si besoin de revenir en arrière.

---

## Exclusions v1 → futures phases

- **Historique inter-runs** (IV Rank, Sizzle Index 30j) → nécessite stockage externe (Supabase ou S3 + SQLite uploadé)
- **Auth / accès privé** → repo privé + GitHub Pro ou Cloudflare Access
- **Scan à la demande depuis l'UI** → nécessite un backend (Cloud Run, Lambda, etc.)
- **Multi-univers simultanés** → matrix strategy dans GHA
- **Notifications push** (scan terminé) → ntfy.sh ou GitHub Actions notification
