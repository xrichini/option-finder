#!/bin/bash
# deploy.sh — Synchro rapide PC → VM via scp (une seule saisie de mdp)
# Usage: bash deploy.sh [--restart]
#
# Astuce: pour ne plus jamais saisir de mdp, copier sa clé SSH une fois :
#   ssh-copy-id devuser@192.168.1.119

VM="devuser@192.168.1.119"
REMOTE_DIR="~/squeeze-finder"
SOCKET="/tmp/ssh-deploy-$$"

echo "📤 Déploiement vers $VM:$REMOTE_DIR ..."

# Ouvrir une connexion SSH persistante (1 seule saisie de mdp)
ssh -nNf -o ControlMaster=yes -o ControlPath="$SOCKET" -o ControlPersist=60 "$VM"

SCP="scp -o ControlMaster=no -o ControlPath=$SOCKET"

# Fichiers racine
$SCP app.py scan_daemon.py start.py requirements.txt deploy.sh \
    "$VM:$REMOTE_DIR/"

# Dossiers source
for DIR in api services models db utils ui; do
  echo "  → $DIR/"
  $SCP -r "$DIR" "$VM:$REMOTE_DIR/"
done

echo "✅ Synchro terminée."

# Fermer la connexion maître
ssh -O exit -o ControlPath="$SOCKET" "$VM" 2>/dev/null

# Optionnel: --restart pour redémarrer le daemon après déploiement
if [[ "$1" == "--restart" ]]; then
  echo "🔄 Redémarrage des services sur la VM..."
  ssh "$VM" bash << 'REMOTE'
    cd ~/squeeze-finder
    source .venv/bin/activate
    pip install -r requirements.txt -q

    # Daemon
    pkill -f scan_daemon.py 2>/dev/null; sleep 1
    nohup python scan_daemon.py --universe nasdaq100 > scan_daemon.log 2>&1 &
    echo "  Daemon PID: $!"

    # Serveur FastAPI (si pas géré par systemd)
    pkill -f 'uvicorn app:app' 2>/dev/null; sleep 1
    nohup uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1 > server.log 2>&1 &
    echo "  Server PID: $!"
REMOTE
  echo "🚀 Services redémarrés. Logs: ssh $VM 'tail -f ~/squeeze-finder/scan_daemon.log'"
fi
