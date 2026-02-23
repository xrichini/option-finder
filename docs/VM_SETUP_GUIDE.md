# Guide déploiement — Scan Daemon sur VM Linux

## Architecture cible

```
VM (Freebox ou VMware)                    PC Client
├── scan_daemon.py                        Browser → http://<IP>:8000
│     └── toutes les 15 min              └── affichage instantané
│           → data/latest_scan.json            (résultats pré-calculés)
└── uvicorn app.py --host 0.0.0.0:8000
      └── GET /api/daemon/latest-scan
```

---

## Option A — Test local sur VirtualBox (recommandé pour commencer)

Créer une VM Ubuntu 24.04 **Server** dans VirtualBox :
- **CPU** : 1, **RAM** : 2048 MB, **Disque** : 20 GB (VDI dynamique)
- **Réseau** : Adaptateur 1 → **Accès par pont / Bridged** ← obligatoire
  (la VM obtient une IP sur ton réseau local, accessible depuis le navigateur PC)

ISO à télécharger (Ubuntu Server, ~1.5 GB, pas Desktop) :
https://ubuntu.com/download/server

Pendant l'installation Ubuntu, cocher **OpenSSH server** quand proposé.

L'avantage : tu testes tout maintenant, et quand la Freebox est prête tu
répètes juste les mêmes étapes.

**VS Code Remote Explorer** fonctionne parfaitement avec VirtualBox Bridged.

---

## Option B — VM Freebox (déploiement final)

### Prérequis hardware
- Un disque dur dans le bay Freebox (SATA 2.5" ou SSD)
- L'interface VM Freebox (Freebox Delta/Ultra uniquement)

### Création de la VM
- **Système** : Ubuntu 24.04 LTS
- **CPU** : 1
- **RAM** : 2 GB minimum (4 GB recommandé)
- **Disque** : 10 GB (20 GB si longévité 2-3 ans)
- **Clé SSH** : coller la clé publique `~/.ssh/id_freebox.pub`

### Générer la clé SSH (depuis PowerShell Windows)
```powershell
ssh-keygen -t ed25519 -C "freebox-vm" -f "$HOME/.ssh/id_freebox" -N ""
cat "$HOME/.ssh/id_freebox.pub"   # copier cette ligne dans le formulaire Freebox
```

---

## Installation sur la VM

### 1. Se connecter en SSH
```bash
# Freebox
ssh -i ~/.ssh/id_freebox xavier@<IP_VM>

# VirtualBox (mot de passe Ubuntu classique)
ssh xavier@<IP_VM>
```

> Récupérer l'IP de la VM : `ip a | grep "inet " | grep -v 127`

> Quitter SSH proprement : `exit`

### 2. Clavier AZERTY (si besoin)
```bash
sudo loadkeys fr   # temporaire pour la session

# Permanent :
sudo dpkg-reconfigure keyboard-configuration
# → Generic 105-key → French → French → No compose key → Yes
sudo reboot
```

### 3. Dépendances système
```bash
sudo apt update
sudo apt install -y git software-properties-common

# Python 3.13 (Ubuntu 24.04 embarque 3.12, on installe 3.13 pour cohérence avec le PC)
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.13 python3.13-venv python3.13-dev

# Vérifier
python3.13 --version   # doit afficher 3.13.x
```

> **Important** : `python3.13-dev` est requis pour compiler les extensions C
> (pandas, numpy). Sans ça, `pip install` échoue avec `Python.h not found`.

> Ubuntu 24.04 n'a pas `python3.11` dans ses dépôts — utiliser le PPA deadsnakes.

### 4. Cloner le projet
```bash
# Le repo est privé → utiliser un Personal Access Token (PAT) GitHub
# Créer le PAT : GitHub → Settings → Developer settings →
#                Personal access tokens → Tokens (classic) → Generate
#                Cocher "repo" → copier le token (ghp_xxx...)

git clone https://xrichini:<TON_PAT>@github.com/xrichini/squeeze-finder.git
cd squeeze-finder
```

### 5. Environnement Python
```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> Si pip install échoue sur pandas/numpy : vérifier que `python3.13-dev`
> est bien installé (étape 3), puis relancer.

### 6. Copier le `.env` (depuis le PC Windows)
```powershell
# Dans PowerShell sur le PC :
scp "D:\XAVIER\DEV\Python Projects\squeeze-finder\.env" xavier@<IP_VM>:~/squeeze-finder/.env
```

### 7. Tester le daemon (un seul scan, ignore les heures de marché)
```bash
source .venv/bin/activate
python scan_daemon.py --once --force
# → doit créer data/latest_scan.json
python -m json.tool data/latest_scan.json | head -30
```

### 7. Lancer le serveur FastAPI
```bash
# Terminal 1
uvicorn app:app --host 0.0.0.0 --port 8000

# Terminal 2
python scan_daemon.py --universe nasdaq100 --interval 15
```

Accès depuis le navigateur PC : `http://<IP_VM>:8000`

---

## Services permanents (systemd)

### scan_daemon.service
```bash
sudo nano /etc/systemd/system/squeeze-scanner.service
```
```ini
[Unit]
Description=Squeeze Finder — Scan Daemon
After=network.target

[Service]
User=xavier
WorkingDirectory=/home/xavier/squeeze-finder
EnvironmentFile=/home/xavier/squeeze-finder/.env
ExecStart=/home/xavier/squeeze-finder/.venv/bin/python scan_daemon.py --universe nasdaq100 --interval 15
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

### squeeze-server.service
```bash
sudo nano /etc/systemd/system/squeeze-server.service
```
```ini
[Unit]
Description=Squeeze Finder — FastAPI Server
After=network.target

[Service]
User=xavier
WorkingDirectory=/home/xavier/squeeze-finder
EnvironmentFile=/home/xavier/squeeze-finder/.env
ExecStart=/home/xavier/squeeze-finder/.venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Activer les deux services
```bash
sudo systemctl daemon-reload
sudo systemctl enable squeeze-scanner squeeze-server
sudo systemctl start squeeze-scanner squeeze-server

# Voir les logs en live
sudo journalctl -fu squeeze-scanner
sudo journalctl -fu squeeze-server
```

---

## Accès depuis l'extérieur (optionnel) — Tailscale

Pour accéder à la VM depuis n'importe où (pas juste réseau local) :

```bash
# Sur la VM :
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
# → affiche une URL à ouvrir dans le navigateur pour autoriser

# Récupérer l'IP Tailscale de la VM :
tailscale ip -4
```

Installer Tailscale sur le PC Windows : https://tailscale.com/download

Accès : `http://<tailscale-ip>:8000` depuis n'importe quel appareil dans ton réseau Tailscale.

---

## VS Code Remote Explorer

L'extension **Remote - SSH** (dans le pack Remote Explorer) est **très utile** :
- Éditer les fichiers de la VM directement dans VS Code (comme en local)
- Terminal intégré sur la VM
- Voir les logs, modifier la config, relancer les services — sans quitter VS Code

### Configuration
```powershell
# Ajouter dans ~/.ssh/config (Windows) :
Host freebox-vm
    HostName <IP_VM>
    User xavier
    IdentityFile ~/.ssh/id_freebox

Host vmware-ubuntu
    HostName <IP_VM_VMWARE>
    User xavier
```

Dans VS Code : **Remote Explorer → SSH → freebox-vm** → Connect.

---

## Endpoints daemon disponibles

| Endpoint | Description |
|---|---|
| `GET /api/daemon/latest-scan` | Résultats du dernier scan (même format que scan normal) |
| `GET /api/daemon/status` | Statut : âge du scan, count, universe, `stale` si > 1h |

---

## Résumé commandes utiles

```bash
# Vérifier que le daemon tourne
sudo systemctl status squeeze-scanner

# Forcer un scan immédiat (hors heures)
python scan_daemon.py --once --force

# Voir les logs du daemon
tail -f scan_daemon.log

# Redémarrer après mise à jour du code
git pull && sudo systemctl restart squeeze-scanner squeeze-server
```
