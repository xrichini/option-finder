# 🌳 Git Branching Strategy Guide

## 🎯 Concept de Base

Une **branche Git** est une ligne de développement indépendante qui permet de :
- **Isoler le travail** : développer une fonctionnalité sans affecter le code principal
- **Collaborer efficacement** : plusieurs développeurs peuvent travailler en parallèle
- **Tester en sécurité** : expérimenter sans risquer de casser la version stable
- **Organiser l'historique** : garder un historique propre et lisible

## 🏗️ Structure des Branches

```
main (production)
├── develop (intégration)
├── feature/streaming-integration
├── feature/keyboard-shortcuts  
├── bugfix/websocket-connection
└── hotfix/critical-error
```

### Types de Branches

| Type | Purpose | Durée de vie | Base |
|------|---------|--------------|------|
| **main** | Code de production stable | Permanent | - |
| **develop** | Intégration des nouvelles fonctionnalités | Permanent | main |
| **feature/** | Développement de nouvelles fonctionnalités | Temporaire | develop |
| **bugfix/** | Correction de bugs non-critiques | Temporaire | develop |
| **hotfix/** | Corrections urgentes en production | Temporaire | main |

## 🚀 Workflow Typique

### 1. Feature Development (Nouvelle fonctionnalité)

```bash
# 1. Se positionner sur la branche de base
git checkout main
git pull origin main

# 2. Créer une branche feature
git checkout -b feature/market-hours-awareness

# 3. Développer la fonctionnalité
# ... faire vos modifications ...
git add .
git commit -m "feat: add market hours detection"

# 4. Push de la branche feature
git push -u origin feature/market-hours-awareness

# 5. Créer une Pull Request (sur GitHub/GitLab)
# ... code review et tests ...

# 6. Merger dans main (après approbation)
git checkout main
git pull origin main
git merge feature/market-hours-awareness

# 7. Supprimer la branche feature
git branch -d feature/market-hours-awareness
git push origin --delete feature/market-hours-awareness
```

### 2. Bug Fix (Correction de bug)

```bash
# 1. Créer une branche bugfix depuis main
git checkout main
git pull origin main
git checkout -b bugfix/websocket-reconnection-error

# 2. Identifier et corriger le bug
# ... corrections ...
git add .
git commit -m "fix: resolve WebSocket reconnection timeout issue"

# 3. Tester la correction
# ... tests ...

# 4. Push et merge
git push -u origin bugfix/websocket-reconnection-error
# ... Pull Request et merge ...
```

### 3. Hotfix (Correction urgente)

```bash
# 1. Branche hotfix depuis main (production)
git checkout main
git pull origin main
git checkout -b hotfix/critical-streaming-crash

# 2. Correction rapide
git add .
git commit -m "hotfix: prevent streaming crash on market close"

# 3. Merge immédiat dans main
git checkout main
git merge hotfix/critical-streaming-crash
git push origin main

# 4. Tag de version patch
git tag -a v2.0.1 -m "Hotfix v2.0.1: Fix critical streaming crash"
git push origin v2.0.1
```

## 📋 Conventions de Nommage

### Préfixes Standards
- `feature/` : Nouvelles fonctionnalités
- `bugfix/` ou `fix/` : Corrections de bugs
- `hotfix/` : Corrections urgentes
- `refactor/` : Refactoring de code
- `docs/` : Modifications de documentation
- `test/` : Ajout/modification de tests

### Exemples pour Votre Projet
```bash
# Fonctionnalités
feature/real-time-streaming
feature/keyboard-shortcuts
feature/market-hours-display
feature/error-handling-enhancement

# Corrections
bugfix/websocket-connection-timeout
bugfix/market-status-display-error
fix/streaming-performance-issue

# Améliorations
refactor/streaming-module-optimization
refactor/ui-components-cleanup

# Documentation
docs/update-readme-streaming
docs/add-api-documentation
```

## 🛠️ Commandes Git Essentielles

### Gestion des Branches
```bash
# Lister toutes les branches
git branch -a

# Créer et basculer vers une nouvelle branche
git checkout -b feature/ma-nouvelle-fonctionnalite

# Basculer vers une branche existante
git checkout main

# Supprimer une branche locale
git branch -d feature/ancienne-fonctionnalite

# Supprimer une branche distante
git push origin --delete feature/ancienne-fonctionnalite

# Voir les branches merged
git branch --merged
```

### Synchronisation
```bash
# Récupérer les dernières modifications
git fetch origin

# Mettre à jour la branche courante
git pull origin nom-de-la-branche

# Rebaser sa branche sur main (garder historique propre)
git rebase main

# Push avec tracking de la branche
git push -u origin feature/ma-branche
```

### Merge vs Rebase
```bash
# Merge (crée un commit de merge)
git checkout main
git merge feature/ma-fonctionnalite

# Rebase (applique les commits un par un)
git checkout feature/ma-fonctionnalite
git rebase main
git checkout main
git merge feature/ma-fonctionnalite  # Fast-forward
```

## 🎯 Exemple Concret : Wheel Strategy Screener

### Scénario : Ajout du système de raccourcis clavier

```bash
# 1. Planification
# Fonctionnalité : Système de raccourcis clavier
# Branche : feature/keyboard-shortcuts
# Base : main (dernière version stable)

# 2. Création de la branche
git checkout main
git pull origin main
git checkout -b feature/keyboard-shortcuts

# 3. Développement (plusieurs commits)
# Ajout du fichier keyboard_shortcuts.py
git add keyboard_shortcuts.py
git commit -m "feat: add keyboard shortcuts module structure"

# Intégration dans l'app principale
git add app.py
git commit -m "feat: integrate keyboard shortcuts in main app"

# Ajout des tests
git add tests/test_keyboard_shortcuts.py
git commit -m "test: add keyboard shortcuts unit tests"

# Mise à jour de la documentation
git add README.md COMMIT_CHEATSHEET.md
git commit -m "docs: update documentation for keyboard shortcuts"

# 4. Push de la branche
git push -u origin feature/keyboard-shortcuts

# 5. Création d'une Pull Request
# Sur GitHub : New Pull Request
# Base: main <- Compare: feature/keyboard-shortcuts
# Titre: "feat: Add keyboard shortcuts system"
# Description: détails de la fonctionnalité

# 6. Code Review et Tests
# Collègues reviewent le code
# Tests automatisés passent
# Corrections si nécessaire avec des commits additionnels

# 7. Merge après approbation
git checkout main
git pull origin main  # S'assurer d'avoir la dernière version
git merge feature/keyboard-shortcuts
git push origin main

# 8. Nettoyage
git branch -d feature/keyboard-shortcuts
git push origin --delete feature/keyboard-shortcuts

# 9. Tag de version (si version majeure/mineure)
git tag -a v2.1.0 -m "Release v2.1.0: Add keyboard shortcuts system"
git push origin v2.1.0
```

## 🔄 Workflow Recommendations

### Pour Développement Solo
```bash
# Workflow simplifié mais propre
main (stable) 
├── feature/nouvelle-fonctionnalite
└── bugfix/correction-rapide
```

### Pour Équipe
```bash
# Workflow GitFlow complet
main (production)
├── develop (intégration)
│   ├── feature/fonctionnalite-a
│   ├── feature/fonctionnalite-b
│   └── bugfix/correction-develop
└── hotfix/correction-urgente
```

## ⚠️ Bonnes Pratiques

### ✅ À FAIRE
- **Branches courtes** : 1-5 jours de travail maximum
- **Commits atomiques** : une modification logique par commit
- **Messages descriptifs** : suivre les conventions (feat:, fix:, docs:)
- **Rebase avant merge** : garder un historique propre
- **Supprimer les branches mergées** : éviter l'encombrement

### ❌ À ÉVITER
- **Branches de longue durée** : difficiles à merger
- **Commits trop gros** : difficiles à reviewer
- **Merge de main dans feature** : pollue l'historique
- **Commits de merge inutiles** : préférer rebase + fast-forward
- **Branches abandonnées** : nettoyer régulièrement

## 🔧 Intégration VS Code

### Extensions Recommandées
- **GitLens** : visualisation avancée de l'historique
- **Git Graph** : vue graphique des branches
- **GitHub Pull Requests** : gestion des PR directement dans VS Code

### Commandes VS Code
- **Ctrl+Shift+G** : Ouvrir l'onglet Source Control
- **Ctrl+Shift+P** → "Git: Create Branch" : créer une branche
- **Ctrl+Shift+P** → "Git: Checkout to" : changer de branche
- **Ctrl+Shift+P** → "Git: Merge Branch" : merger une branche

### Configuration VS Code
```json
// .vscode/settings.json
{
  "git.enableSmartCommit": true,
  "git.confirmSync": false,
  "git.autofetch": true,
  "git.pruneOnFetch": true,
  "gitlens.currentLine.enabled": true,
  "gitlens.hovers.currentLine.over": "line"
}
```

## 📈 Workflow pour Votre Projet

### Structure Recommandée
```
wheel-strategy-screener/
├── main (v2.0.0 - stable avec streaming)
├── feature/options-Greeks-calculator
├── feature/portfolio-tracking
├── bugfix/streaming-reconnection
└── docs/api-documentation
```

### Exemple de Planning
```bash
# Semaine 1 : Calculateur de Greeks
git checkout -b feature/options-greeks-calculator

# Semaine 2 : Suivi de portfolio  
git checkout main
git checkout -b feature/portfolio-tracking

# Bug critique découvert
git checkout main
git checkout -b hotfix/streaming-memory-leak
# ... correction immédiate et merge
```
