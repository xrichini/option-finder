# ⌨️ Git Shortcuts Quick Reference

## 🚀 Workflows Git (Tâches Personnalisées)

| Raccourci | Action | Description |
|-----------|--------|-------------|
| `Ctrl+Shift+G Ctrl+F` | **🌟 Start New Feature** | Crée une branche feature/ depuis main |
| `Ctrl+Shift+G Ctrl+B` | **🐛 Start Bug Fix** | Crée une branche bugfix/ depuis main |
| `Ctrl+Shift+G Ctrl+H` | **🚨 Start Hotfix** | Crée une branche hotfix/ depuis main |
| `Ctrl+Shift+G Ctrl+M` | **🔄 Finish Feature** | Push, merge et supprime la branche |
| `Ctrl+Shift+G Ctrl+S` | **📊 Show Branch Status** | Affiche l'état des branches |
| `Ctrl+Shift+G Ctrl+C` | **🧹 Clean Merged Branches** | Supprime les branches mergées |
| `Ctrl+Shift+G Ctrl+P` | **📤 Push Current Branch** | Push la branche courante |
| `Ctrl+Shift+G Ctrl+R` | **🏷️ Create Release Commit** | Aide au commit de release |

## 🔧 Commandes Git de Base

| Raccourci | Action | Description |
|-----------|--------|-------------|
| `Ctrl+G Ctrl+B` | **Switch Branch** | Changer de branche |
| `Ctrl+G Ctrl+S` | **Stage Changes** | Ajouter fichiers au staging |
| `Ctrl+G Ctrl+U` | **Unstage Changes** | Retirer du staging |
| `Ctrl+G Ctrl+I` | **Commit** | Créer un commit |
| `Ctrl+G Ctrl+P` | **Push** | Push vers remote |
| `Ctrl+G Shift+P` | **Pull** | Pull depuis remote |
| `Ctrl+G Ctrl+M` | **Merge Branch** | Merger une branche |

## 👁️ GitLens - Visualisation & Historique

| Raccourci | Action | Description |
|-----------|--------|-------------|
| `Ctrl+G Ctrl+L` | **Repository History** | Historique complet du repo |
| `Ctrl+G Ctrl+G` | **Git Graph** | Vue graphique des branches |
| `Ctrl+G Ctrl+D` | **Diff with Previous** | Comparaison avec version précédente |
| `Ctrl+G Ctrl+H` | **File History** | Historique du fichier courant |
| `Ctrl+G Ctrl+T` | **Line History** | Historique de la ligne courante |
| `Ctrl+G Ctrl+A` | **Repositories View** | Vue des repositories |
| `Ctrl+G Ctrl+C` | **Commits View** | Vue des commits |

## 🎯 Raccourcis Rapides

| Raccourci | Action | Description |
|-----------|--------|-------------|
| `Ctrl+Alt+G` | **Source Control Panel** | Ouvrir l'onglet Git |
| `Ctrl+Shift+Alt+G` | **Git Graph** | Ouvrir directement Git Graph |
| `Ctrl+G Escape` | **Git Commands** | Menu rapide commandes Git |

## 💡 Conseils d'Utilisation

### **Workflow Typique avec Raccourcis**
1. **`Ctrl+Shift+G Ctrl+F`** → Créer nouvelle feature
2. Développer votre fonctionnalité...
3. **`Ctrl+G Ctrl+S`** → Stage les changements
4. **`Ctrl+G Ctrl+I`** → Commit
5. **`Ctrl+Shift+G Ctrl+M`** → Finish feature (push + merge)

### **Exploration avec GitLens**
- **`Ctrl+G Ctrl+G`** → Vue graphique pour comprendre les branches
- **`Ctrl+G Ctrl+H`** → Voir l'évolution d'un fichier
- **`Ctrl+G Ctrl+D`** → Comparer versions rapidement

### **Debug & Investigation**
- **`Ctrl+G Ctrl+L`** → Historique complet du projet
- **`Ctrl+G Ctrl+T`** → Qui a modifié cette ligne ?
- **`Ctrl+G Ctrl+C`** → Explorer tous les commits

## 🔥 Exemples Pratiques

### Créer une nouvelle fonctionnalité
```
Ctrl+Shift+G Ctrl+F
→ Saisir: feature/options-greeks-calculator
→ La branche est créée et active !
```

### Corriger un bug urgent
```
Ctrl+Shift+G Ctrl+H  
→ Saisir: hotfix/streaming-memory-leak
→ Correction, puis Ctrl+Shift+G Ctrl+M
```

### Explorer l'historique d'un fichier
```
Ouvrir le fichier → Ctrl+G Ctrl+H
→ Voir tous les changements dans GitLens
```

### Voir l'état des branches
```
Ctrl+Shift+G Ctrl+S
→ Affiche: branche courante, branches disponibles, commits récents
```

## ⚙️ Configuration Avancée

### Personnaliser les Raccourcis
Si vous voulez modifier un raccourci :
1. **Ctrl+Shift+P** → "Preferences: Open Keyboard Shortcuts (JSON)"
2. Modifier le raccourci souhaité
3. Sauvegarder

### Raccourcis Contextuels
Certains raccourcis ne fonctionnent que dans certains contextes :
- **File history** : seulement quand un fichier est ouvert
- **Line history** : seulement avec le curseur sur une ligne
- **Branch operations** : seulement dans un repo Git

## 🎨 GitLens - Fonctionnalités Visuelles

### Annotations Inline
GitLens affiche automatiquement :
- **Auteur** et **date** de la dernière modification
- **Message de commit** sur chaque ligne
- **Âge relatif** des modifications

### Hover Information
Survolez une ligne pour voir :
- **Détails du commit**
- **Changements associés**  
- **Liens vers les commits liés**

### Blame View
Clic droit → "Toggle Git Blame" pour voir :
- **Historique ligne par ligne**
- **Navigation dans les commits**
- **Comparaisons rapides**

Avec cette configuration, vous avez un workflow Git ultra-rapide directement dans VS Code ! 🚀