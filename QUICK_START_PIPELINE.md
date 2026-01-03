# ⚡ Quick Start - Opportunity Detection Pipeline

## 🎯 What This App Does

Your app detects potential **squeeze opportunities** by analyzing stocks with high short interest and their options markets.

### The 3-Step Pipeline

```
1️⃣ FIND STOCKS       → Filter by short interest + market cap + volume
2️⃣ ANALYZE OPTIONS   → Find unusual options activity (whales)
3️⃣ AI RECOMMENDATIONS → Get AI insights (coming soon)
```

---

## 🚀 How to Use Today (v1.0)

### Start the App
```bash
# Terminal 1: Start FastAPI server
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000

# Terminal 2: Open browser
http://localhost:8000
```

### Run the Pipeline

#### Step 1️⃣: Set Your Filters (Left Sidebar)

```
Short Interest Section:
├─ Exchange: [NASDAQ ▼]           # US exchange
├─ Min Short Interest: [20%]      # Minimum short squeeze %
├─ Min Market Cap: [100M ▼]       # Market size filter
└─ Min Volume: [500K ▼]           # Stock trading volume

Options Analysis Section:
├─ Min Volume: [50]               # Contracts per option
├─ Min IV: [20%]                  # Implied volatility
├─ Max DTE: [45]                  # Days to expiration
└─ Min Whale Score: [50]          # Unusual activity threshold
```

#### Step 2️⃣: Click Main Button

```
📊 SHORT INTEREST → OPTIONS
  ↓
  System:
  1. Finds tickers matching your criteria
  2. Analyzes their options chains
  3. Scores each option by whale activity
  ↓
  Result: List of opportunities
```

#### Step 3️⃣: Review Results

```
Results Display:
├─ Card per opportunity
├─ Shows: Ticker, Option, IV, Greeks, Whale Score
├─ Sortable by: Score, Volume, Price, etc.
├─ Filterable by: Type, Score, Volume
└─ If results exist → AI button appears
```

---

## 🤖 AI Deep Dive (Coming Soon)

When results are found, an "🤖 AI Deep Dive Analysis" button appears:

```
📊 SHORT INTEREST → OPTIONS    [Main pipeline]
🤖 AI DEEP DIVE ANALYSIS      [Appears only with results]
  ↓
  Provides:
  - Squeeze probability
  - Technical analysis
  - Risk assessment
  - Recommended strategies
```

---

## 📊 Using Filter Presets

The advanced filtering panel has 6 presets:

| Preset | Use Case | Settings |
|--------|----------|----------|
| **Balanced** | Most users | Score≥50, Price≤$5, Vol≥75 |
| **Aggressive** | High whale activity | Score≥70, Price≤$2, Vol≥100 |
| **Conservative** | Lower risk | Score≥40, Price≤$10, OI≥100 |
| **High IV** | Volatility trades | IV≥50%, Vol≥50 |
| **Near-Term** | This week | DTE 0-7 |
| **Medium-Term** | Next 2-4 weeks | DTE 7-30 |

**How to use:**
1. Run pipeline ("Short Interest → Options")
2. Click "Filtres Avancés" button
3. Select a preset or customize
4. Results filter instantly

---

## 🔄 Real-Time Updates

The app uses **WebSocket** for live data:

```
✅ Results update in real-time as new opportunities found
✅ Whale scores refresh automatically
✅ Connection status shown in UI
✅ Auto-reconnects if connection lost
```

---

## 📋 Options Card Information

Each opportunity shows:

```
┌─────────────────────────────────────────┐
│ AAPL 240315C150 (Call, March 15)       │
├─────────────────────────────────────────┤
│ Score: 78.5/100  ⭐⭐⭐⭐⭐             │
│ Price: $2.50                            │
│ Volume: 1,250 contracts                 │
│ Open Interest: 800                      │
│ IV: 45% | Delta: 0.65 | Theta: -0.12  │
│ Whale Activity: 🐋🐋🐋 (High)         │
│ Days to Expiration: 15                  │
└─────────────────────────────────────────┘
```

---

## 💾 Saving Your Settings

✅ Filters save automatically to browser storage:
- Selected preset
- Custom filter values  
- Sidebar configuration
- Column preferences

📂 Load previous settings anytime:
```
[Filtres Avancés] → [Charger]
```

---

## 🔧 Troubleshooting

### No Results Found
- Check if tickers exist with your criteria
- Lower "Min Short Interest" threshold
- Increase "Min Market Cap" filter
- Try different exchange

### AI Button Doesn't Appear
- Need opportunities first (run Step 2 first)
- Button only shows if results exist
- Refresh page if stuck

### Slow Loading
- Reduce number of symbols
- Increase DTE range (more contracts to analyze)
- Decrease whale score threshold

### Real-Time Updates Not Working
- Check console for WebSocket errors
- Verify server is running
- Try page refresh
- Check browser connection

---

## 🎯 Example Workflow

### Morning Routine (5 minutes)

```
1. Open app (http://localhost:8000)
2. Keep sidebar settings from yesterday
3. Click "📊 Short Interest → Options"
4. Wait for results (~2 seconds)
5. Review opportunities found
6. Note interesting tickers
7. Close app
   ↓
[Optional] Later: Click "🤖 AI Deep Dive" on interesting ticker
```

### Detailed Analysis (15 minutes)

```
1. Run pipeline with specific filters
2. Results appear → Filter by "High Score"
3. Click "Filtres Avancés" panel
4. Apply "Aggressive" preset
5. Sort by "Whale Score"
6. Review top 5 opportunities
7. [TODO] Use AI Deep Dive for each
8. Export/note candidates
```

---

## 📱 API Usage (Advanced)

### Direct API Calls

```bash
# Step 1: Get tickers with short interest
curl -X GET "http://localhost:8000/api/short-interest/symbols?exchange=nasdaq&min_short_interest=20"

# Step 2: Analyze options
curl -X POST "http://localhost:8000/api/hybrid/scan-all" \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["AAPL", "TSLA"],
    "min_volume": 50,
    "min_whale_score": 50
  }'

# Step 3: Apply filtering
curl -X POST "http://localhost:8000/api/filtering/apply-preset?preset_name=aggressive"
```

---

## ⚙️ Configuration

### Sidebar Settings Explained

**Short Interest Filters:**
- **Exchange**: NASDAQ (tech heavy), NYSE (large cap), AMEX (smaller)
- **Min Short Interest**: 20-50% typical range
- **Market Cap**: 100M-1B (market size bracket)
- **Volume**: 500K-2M shares/day typical

**Options Analysis:**
- **Min Volume**: 50+ (liquid contracts)
- **Min IV**: 20-50% (volatility range)
- **Max DTE**: 7-60 days (expiration preference)
- **Min Whale Score**: 40-80 (activity threshold)

**Type Filters:**
- Call: Right to buy (bullish)
- Put: Right to sell (bearish)
- Both: Show all opportunities

---

## 📊 What Gets Saved

✅ Browser Storage (persists across sessions):
- Filter presets
- Sidebar configuration
- Column sorting preference
- Dark/Light theme

❌ Not Saved (per session):
- Results history
- Scan logs
- Performance data

---

## 🚀 Next Features (v1.1+)

```
📋 In Development:
├─ AI Deep Dive Analysis (Step 3)
├─ Historical performance tracking
├─ Email alerts
├─ Custom preset builder
└─ Results export (CSV/JSON)

🔮 Future (v2.0):
├─ Backtesting framework
├─ Mobile app
├─ Advanced Greeks analysis
└─ Market correlation matrix
```

---

## 🆘 Need Help?

### Documentation
- **Pipeline Details**: See `PIPELINE_DEFINITION.md`
- **Feature Implementation**: See `FEATURES_IMPLEMENTATION.md`
- **Quick Filters Guide**: See `QUICK_START_FILTERS.md`

### Files to Know
```
📁 ui/index.html              → Main interface
📁 api/short_interest_endpoints.py  → Step 1 API
📁 api/hybrid_endpoints.py    → Step 2 API
📁 services/advanced_filtering_service.py → Filtering logic
```

### Check App Status
```bash
# Run verification tests
python test_app_startup.py

# View recent commits
git log --oneline -10

# Check for errors
grep -r "ERROR\|FAIL" *.py
```

---

## 📈 Version Info

- **Current Version**: v1.0
- **Release Date**: Jan 3, 2026
- **Status**: Production Ready (Steps 1-2)
- **Step 3 Status**: In Development
- **Test Coverage**: 51+ tests passing ✅

---

**Last Updated**: Jan 3, 2026  
**Need more details?** Check the main README.md or PIPELINE_DEFINITION.md
