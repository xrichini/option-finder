# VPS Setup Guide — option-finder

Serveur cible : **Hetzner CAX11** (2 vCPU ARM64, 4 GB RAM, 40 GB NVMe) — Ubuntu 24.04 LTS

---

## 1. Installer Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Se déconnecter/reconnecter pour appliquer le groupe
newgrp docker
```

---

## 2. Cloner le repo

```bash
git clone https://github.com/TON_USER/option-finder.git /opt/option-finder
cd /opt/option-finder
```

> Le repo contient déjà `data/options_history.db` et `data/latest_scan.json` (committés par les anciens GitHub Actions runs). **Pas de copie manuelle de la DB nécessaire.**

---

## 3. Créer le fichier `.env`

C'est **le seul fichier à créer manuellement** (non versionné dans git).

**Option A — depuis le VPS directement :**
```bash
cp .env.example .env
nano .env   # remplir les clés API
```

**Option B — copier depuis ton PC (Windows) :**
```bash
scp "d:\XAVIER\DEV\Python Projects\option-finder\.env" user@vps-ip:/opt/option-finder/.env
```

Variables requises (voir `.env.example`) :
| Variable | Description |
|---|---|
| `TRADIER_API_KEY_PRODUCTION` | Clé API Tradier (production) |
| `FMP_API_KEY` | Financial Modeling Prep |
| `POLYGON_API_KEY` | Polygon.io |
| `OPENAI_API_KEY` | OpenAI (optionnel — enrichissement IA) |

---

## 4. Démarrer les services

```bash
cd /opt/option-finder
docker compose up -d --build
```

Le premier `--build` prend ~3–5 minutes (téléchargement des dépendances Python).

Suivre les logs en temps réel :
```bash
docker compose logs -f
```

---

## 5. Vérifier

```bash
# API répond
curl http://localhost:8000/api/daemon/status

# Statut des conteneurs
docker compose ps
```

Dans le navigateur sur ton PC :
```
http://vps-ip:8000
```

---

## 6. Commandes utiles

```bash
# Voir les logs du daemon (scans)
docker compose logs -f daemon

# Voir les logs de l'API
docker compose logs -f api

# Redémarrer après un git pull
git pull
docker compose up -d --build

# Arrêter les services
docker compose down

# Vérifier l'espace disque (DB)
du -sh /opt/option-finder/data/
```

---

## Architecture

```
VPS (port 8000)
├── service api     → FastAPI + UI  (uvicorn app:app)
└── service daemon  → Scans continus toutes les 15 min
                      nasdaq100 → sp500 → dow30 (séquentiel)
                      Actif seulement quand marché ouvert (NYSE)
                      ↓
                    ./data/  (bind mount partagé)
                    ├── latest_scan.json   ← résultats du dernier scan
                    └── options_history.db ← historique SQLite
```

---

## Mise à jour du code

```bash
cd /opt/option-finder
git pull
docker compose up -d --build
```

---

## Migration DB depuis GitHub (si nécessaire)

Si la DB locale sur ton PC est plus récente que celle du repo :

```bash
# Depuis ton PC (Windows)
scp "d:\XAVIER\DEV\Python Projects\option-finder\data\options_history.db" \
    user@vps-ip:/opt/option-finder/data/options_history.db
```
