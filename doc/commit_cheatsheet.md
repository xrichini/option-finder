# 🚀 Git Commit Process Cheat Sheet

## 🏷️ Version Types
- **Major (x.0.0)**: Breaking changes, new architecture
- **Minor (x.y.0)**: New features, backward compatible  
- **Patch (x.y.z)**: Bug fixes, no new features

## ⚡ Quick Commands

### 1. Stage Changes
```bash
git add .
```

### 2. Commit with Conventional Format
```bash
git commit -m "feat: Brief description

BREAKING CHANGE: 
- New dependencies: package>=version
- New files: filename.py
- Architecture changes

Features:
- Feature 1 description
- Feature 2 description

Technical Improvements:
- Performance optimization
- Error handling enhancement"
```

### 3. Create Version Tag
```bash
git tag -a v2.0.0 -m "Release v2.0.0: Description"
```

### 4. Push with Tags
```bash
git push origin main --tags
```

## 📝 Commit Message Templates

### Major Release Template
```
feat: Enhanced [main feature name]

BREAKING CHANGE:
- New required dependencies: [list]
- New required files: [list]
- [Other breaking changes]

Features:
- [Feature 1]
- [Feature 2]
- [Feature 3]

Technical Improvements:
- [Improvement 1]
- [Improvement 2]
```

### Minor Release Template  
```
feat: Add [feature name]

Features:
- [New feature description]
- [Enhancement description]

Improvements:
- [Improvement 1]
- [Bug fix 1]
```

### Patch Release Template
```
fix: [bug description]

- Fixed [specific issue]
- Improved [specific area]
- Updated [specific component]
```

## 🎯 Current Project Status

**Next Version**: v2.0.0 (Major)
**Reason**: Enhanced live streaming integration with breaking changes

**Breaking Changes**:
- New dependency: `pytz>=2023.3`
- New files: `market_utils.py`, `keyboard_shortcuts.py`
- Enhanced streaming module architecture

## 📋 Pre-Commit Checklist

- [ ] All new files added to git
- [ ] README.md updated
- [ ] Version number determined
- [ ] Breaking changes documented
- [ ] Tests passing (if applicable)
- [ ] VS Code tasks working correctly

## 🔄 VS Code Tasks Available

- **Ctrl+Shift+P** → "Tasks: Run Task" → "🏷️ Create Release Commit"
- **Ctrl+Shift+P** → "Tasks: Run Task" → "📝 Generate Commit Template"  
- **Ctrl+Shift+P** → "Tasks: Run Task" → "🏷️ Create Version Tag"
- **Ctrl+Shift+P** → "Tasks: Run Task" → "🚀 Push with Tags"