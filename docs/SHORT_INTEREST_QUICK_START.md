# 🎯 Short Interest → Options Pipeline - Quick Start Guide

## 📖 Overview

The Short Interest functionality allows you to automatically screen for options on stocks with high short interest, potentially identifying squeeze opportunities and unusual options activity.

## 🚀 How to Use

### Method 1: Direct Pipeline (Recommended)
1. **Keep default settings** in the sidebar (manual symbols mode)
2. **Click "🎯 Short Interest → Options"** button in the main controls
3. The system will:
   - Fetch symbols with high short interest (>20%, >100M market cap, >500K volume)
   - Run options screening on those symbols
   - Display results with 🎯 badges for Short Interest symbols

### Method 2: Configure Short Interest Mode
1. **Enable Short Interest mode** by checking "Utiliser les symboles avec Short Interest élevé" in sidebar
2. **Configure filters**:
   - Exchange: NASDAQ, NYSE, AMEX, or All
   - Short Interest minimum: 20% (recommended)
   - Market cap minimum: 100M $ (recommended)
   - Stock volume minimum: 500K (recommended)
3. **Watch symbols auto-load** in the status area
4. **Click "🎯 Short Interest → Options"** to run the pipeline

## ⚙️ Configuration Options

### 🎯 Short Interest Filters
- **Exchange**: Target market (NASDAQ recommended for tech stocks)
- **Min Short Interest**: Higher = more squeeze potential (20-30% sweet spot)
- **Min Market Cap**: Larger companies = more liquid options (100M+ recommended)
- **Min Stock Volume**: Higher = more active stocks (500K+ recommended)

### 📊 Options Screening (from sidebar)
- **Volume Minimum**: 50+ contracts (higher for better liquidity)
- **Max DTE**: 45 days (shorter for squeeze plays)
- **Whale Score**: 50+ (higher indicates unusual activity)
- **IV Minimum**: 20% (higher for volatility plays)

## 🔍 What to Look For

### 🎯 High-Priority Signals
1. **Short Interest badges** (🎯) on option cards = came from Short Interest screening
2. **High volume calls** on high short interest stocks = potential squeeze setup
3. **Unusual put activity** = hedge positions or additional bearish bets
4. **Near-term expiry** with high volume = catalyst plays

### 📈 Ideal Combinations
- High short interest (>25%) + High call volume + Near expiry (7-21 DTE)
- Moderate short interest (15-25%) + Very high call volume + Good liquidity
- High short interest + Put/Call ratio changes + Recent news/catalyst

## 🎨 Visual Indicators

### 🎯 Option Cards
- **🎯 Badge**: Symbol came from Short Interest screening
- **Red border** (PUT): Bearish option on high short interest stock
- **Green border** (CALL): Bullish option on high short interest stock (squeeze potential)

### 📊 Status Messages
- **Blue**: Informational
- **Green**: Success/loaded
- **Yellow**: Loading/warning
- **Red**: Error

## 🔄 Workflow Examples

### Squeeze Hunter Workflow
```
1. Set Short Interest minimum to 25%
2. Set DTE maximum to 21 days
3. Set Whale Score minimum to 60
4. Run "Short Interest → Options"
5. Look for CALL options with 🎯 badge
6. Focus on high volume, near expiry
```

### Volatility Play Workflow
```
1. Set Short Interest minimum to 15%
2. Set IV minimum to 30%
3. Set Volume minimum to 100
4. Run "Short Interest → Options"
5. Look for both CALL and PUT activity
6. Monitor volume spikes
```

### Hedge Detection Workflow
```
1. Set Short Interest minimum to 20%
2. Focus on PUT options with 🎯 badge
3. Look for unusual volume vs open interest
4. May indicate institutional hedging
```

## 🚨 Risk Considerations

### ⚠️ Important Notes
- **High short interest ≠ guaranteed squeeze** - need catalyst
- **Options on shorted stocks can be volatile** - size positions appropriately
- **Liquidity varies** - check bid/ask spreads before trading
- **Time decay** - short DTE options lose value quickly

### 🎯 Best Practices
1. **Combine with other analysis** - don't rely solely on short interest
2. **Monitor news/catalysts** - earnings, FDA approvals, etc.
3. **Check float size** - smaller float = higher squeeze potential
4. **Watch institutional ownership** - high ownership can limit squeeze
5. **Use stop losses** - volatility can work against you

## 🔧 Troubleshooting

### No symbols loaded?
- Check internet connection
- Try different exchange (NASDAQ usually has most data)
- Lower short interest minimum (try 15%)
- Lower market cap minimum (try 50M)

### No options found?
- Lower whale score minimum
- Increase DTE maximum (try 60 days)
- Lower volume minimum
- Check if markets are open

### Slow loading?
- Normal for first load (scraping + enrichment)
- Subsequent loads use cached data
- Consider smaller symbol sets

## 📚 Advanced Tips

### 🎯 Multi-Timeframe Analysis
1. Run with DTE 7-14 for short-term plays
2. Run with DTE 30-60 for swing trades
3. Compare volume patterns across timeframes

### 📊 Pattern Recognition
- **Volume spikes** on high SI stocks before earnings
- **Put/call ratio** inversions
- **IV expansion** ahead of squeeze events

### 🔍 Combine Filters
- High short interest + High IV + Recent news
- Moderate short interest + Huge volume + Low DTE
- Any short interest + Unusual whale activity + Catalyst timing

---

**🎯 Ready to Hunt for Squeeze Plays?**
Start with the default settings and click "🎯 Short Interest → Options" to begin!