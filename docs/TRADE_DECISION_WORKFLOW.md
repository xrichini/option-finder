# 🎯 Trade Decision Workflow - From Scan to Action

**Date**: April 2026  
**Status**: Current (Multi-Universe Scanning)  
**Challenge**: Many tickers score 100/100 — need multi-stage filtering to differentiate

---

## Problem: Score Compression at 100/100

**Observation**: With ~630 opportunities per scan, many have `whale_score: 100.0`

**Root Cause**: Whale score is a **bullish signal detector**, not a **trade ranking system**
- If a contract shows multiple signals (high vol + tight spread + OI spike), it hits 100
- But this doesn't mean **all 100-score options are equal quality**

**Solution**: Use **secondary filters** (Stage 2) to rank within the same score bucket

---

## 📊 Stage 1: Scan Results Overview

### What Happens
- **Frequency**: Every 15 minutes during market hours (9:30 AM - 4 PM ET)
- **Coverage**: 630 total opportunities across 3 universes
  - NASDAQ 100: ~80-90 options
  - S&P 500: ~150-200 options
  - DOW 30: ~20-30 options
- **Output**: `data/latest_scan.json` (merged, deduplicated, sorted by whale_score DESC)

### What You See in UI
```
┌─ Universe Filter ─────────────────────┐
│ [All Universes ▼]                     │
│ ├─ All Universes                      │
│ ├─ NASDAQ 100                         │
│ ├─ S&P 500                            │
│ └─ DOW 30                             │
└───────────────────────────────────────┘

┌─ Score Badges (Color-coded) ───────────┐
│ 🟢 100.0  🟢 100.0  🟡 95.2  🔴 75.0  │
│           (many 100's at top)         │
└────────────────────────────────────────┘

┌─ Sortable Table (21 columns) ──────────┐
│ Symbol │ Side │ Strike │ Vol │ Score   │
├────────┼──────┼────────┼─────┼─────────┤
│ MSTR   │ 📈   │ $160   │ 24k │ 100.0 ◇ │ ← 100 with sparkline
│ NVDA   │ 📈   │ $130   │ 18k │ 100.0 ◇ │
│ AAPL   │ 📈   │ $180   │ 15k │ 99.8  ◇ │
│ TSLA   │ 📈   │ $250   │ 12k │ 95.2    │
└────────┴──────┴────────┴─────┴─────────┘
```

---

## 🔍 Stage 2: **Primary Differentiation** (How to choose between 100/100 scores)

### 2.1 Volume Filtering (Most Important for Whales)

**Logic**: Big volume = liquidity + conviction  
**Action**: Sort by `volume` DESC or apply `Min Vol` filter

| Volume Range | Interpretation | Trade Quality |
|---|---|---|
| **> 50k contracts** | Massive block trades, institutional | 🟢 **PRIORITY** |
| **10k - 50k** | Strong retail + institutional | 🟡 Good |
| **2k - 10k** | Retail interest | ⚪ Decent |
| **< 2k** | Thinly traded | 🔴 Avoid |

**Where to find**: Column `Vol` in table (sortable)  
**Quick action**: Apply filter `Min Vol: 10000` to focus on liquid options

---

### 2.2 Spread Analysis (Institutional Signature)

**Logic**: Tight bid-ask spread = market makers interested = real opportunity  
**Calculation**: Included in whale_score as +5 to +7.4 points (Spread Compression signal)

| Spread Width | Signal | What it means |
|---|---|---|
| **< 0.5%** | Very tight | Institutional flow likely |
| **0.5% - 1%** | Tight | Some institutional interest |
| **1% - 2%** | Normal retail | Regular market conditions |
| **> 2%** | Wide | Low interest, avoid |

**How to check**:
1. Click on any row in the table
2. See `Bid` / `Ask` columns → calculate spread width
3. Example: Bid=$10.80, Ask=$11.05 → Spread = $0.25 = 2.3% (normal)

---

### 2.3 Volume-to-Open Interest Ratio (Flow Intensity Without OI Change)

**Logic**: VOL/OI ratio shows how much of today's total OI moved as volume  
- **High ratio (> 0.5)** = Intense flow activity, new positioning
- **Low ratio (< 0.1)** = Thin flow relative to existing OI

| VOL/OI Ratio | Interpretation | Trade Quality |
|---|---|---|
| **> 1.0** | Extreme flow (more than daily average) | 🟢 **HOTTEST CONTRACTS** |
| **0.5 - 1.0** | Strong flow intensity | 🟡 Good momentum |
| **0.2 - 0.5** | Moderate flow | ⚪ Decent |
| **< 0.1** | Minimal relative flow | 🔴 Avoid |

**Why it matters**: 
- High VOL/OI = Today's volume is large compared to standing interest
- Suggests traders are building **new positions** (not just rolling old ones)
- Better indicator than raw volume alone

**Where to find**: Column `VOL/OI` in table (directly visible, sortable)  
**Quick action**: Sort by `VOL/OI` DESC to find hottest contracts

---

### 2.4 Put/Call Flow Ratio (Hedging vs Accumulation)

**Logic**:
- **High Put/Call ratio** = Defensive hedging (bearish)
- **Low Put/Call ratio** = Call accumulation (bullish)

| Ratio | Signal | Trade Type |
|---|---|---|
| **Put/Call > 1.5** | Defensive buying | Avoid calls, consider puts |
| **0.67 < Put/Call < 1.5** | Neutral | Check other signals |
| **Put/Call < 0.67** | Call accumulation | 🟢 **BUY CALLS** |

**How to verify**: 
- Check if most 100-score opportunities are **Calls** (bullish) vs **Puts** (defensive)
- Batch analysis: If 80% of top scores are Calls, market is bullish

---

## 📈 Stage 3: **Secondary Analysis** (For Top 20 After Stage 2)

Once you've filtered to ~20 quality options using Volume + OI Momentum, analyze:

### 3.1 Earnings Calendar (⚡ Column)

| ⚡ Status | Days to Earnings | Trading Strategy |
|---|---|---|
| 🔴 **⚡ EARNINGS** | Within 7 days | High IV, watch for IV crush post-earnings |
| ⚪ No ⚡ | > 7 days | Normal IV behavior, safer |

**Action**: Skip earnings week unless you're specialized in earnings plays

---

### 3.2 Beta / Volatility Profile (Column `Beta`)

| Beta | Stock Type | Strategy |
|---|---|---|
| **> 1.5** (Red) | 🚀 High beta (growth) | Higher risk/reward, use smaller size |
| **1.0 - 1.5** (Orange) | 🟡 Medium beta | Balanced, good for swing trades |
| **< 1.0** (Gray) | 🔵 Defensive (stable) | Lower risk, good for income strategies |

**Correlation**: High beta + high volume = speculative whale play  
Lower beta + high volume = institutional conviction play (higher quality)

---

### 3.3 Insider Trading Activity (Insider Column)

| Sentiment | What it means | Action |
|---|---|---|
| 🟢 **BULLISH** | Insiders bought recently | Additional confirmation to buy calls |
| ⚪ **NEUTRAL** | No recent insider activity | Use technical signals only |
| 🔴 **BEARISH** | Insiders sold recently | Avoid calls, consider puts |

**Data source**: Last 30 days of insider trades (Finviz)  
**Note**: Mega-caps often show neutral (less insider disclosure)

---

## 🎯 Stage 4: **Make the Trade Decision** (Decision Tree)

```
START: You have a 100/100 whale option
  │
  ├─→ Check Volume (Liquidity)
  │    ├─ If < 5k: SKIP (too illiquid)
  │    └─ If >= 5k: CONTINUE
  │
  ├─→ Check VOL/OI Ratio (Flow Intensity)
  │    ├─ If < 0.1: SKIP (minimal relative flow)
  │    ├─ If 0.1 to 0.5: ⚪ NEUTRAL (continue checking)
  │    ├─ If 0.5 to 1.0: 🟡 GOOD FLOW
  │    └─ If > 1.0: 🟢 **HOTTEST** (build new positions)
  │
  ├─→ Check Delta (Directional Bias)
  │    ├─ If Delta > 0.6 (calls): 🟢 Strong bullish
  │    ├─ If Delta 0.4-0.6: 🟡 Near ATM (high risk/reward)
  │    ├─ If Delta < 0.3 (calls): 🔴 Far OTM (lottery)
  │    └─ (Reverse logic for puts)
  │
  ├─→ Check Put/Call Flow
  │    ├─ If mostly PUTS: SKIP (defensive)
  │    └─ If mostly CALLS: 🟢 BULLISH
  │
  ├─→ Check Earnings (⚡)
  │    ├─ If ⚡ (within 7d): ⚠️ HIGH IV RISK
  │    └─ If no ⚡: ✅ NORMAL CONDITIONS
  │
  ├─→ Check IV Rank (IVR column)
  │    ├─ If IVR > 80%: 🟢 Elevated volatility, good for selling premium
  │    ├─ If IVR 30-80%: 🟡 Normal range
  │    └─ If IVR < 30%: ⚪ Low volatility (wait for expansion)
  │
  ├─→ Check Beta (Risk Profile)
  │    ├─ If Beta > 2.0 + Vol > 50k: 🚀 SPECULATIVE WHALE
  │    ├─ If Beta < 1.3 + Vol > 20k: 🟢 INSTITUTIONAL
  │    └─ Otherwise: 🟡 RETAIL
  │
  ├─→ Check Insider Sentiment
  │    ├─ If 🟢 BULLISH: Additional confirmation
  │    └─ If 🔴 BEARISH: Second thought before buying
  │
  └─→ DECISION
       ├─ STRONG BUY: High volume + OI up + Insider bullish + No earnings
       ├─ BUY: Volume > 20k + OI stable+ Bullish sentiment
       ├─ HOLD / WATCH: Mixed signals, need more data
       └─ SKIP: Low volume OR OI falling OR Insider bearish
```

---

## 💡 Practical Example Walkthrough

### Scenario: You see these three at 100.0 score

| # | Symbol | Vol | OI Change | Put/Call | Beta | Insider | Earnings |
|---|---|---|---|---|---|---|---|
| 1 | MSTR | 24,052 | +45% | 0.45 (Call heavy) | 1.8 | 🟢 BULLISH | ⚪ None |
| 2 | NVDA | 18,200 | -8% | 0.88 (Neutral) | 1.2 | ⚪ NEUTRAL | ⚪ None |
| 3 | AAPL | 6,800 | +12% | 1.1 (Neutral) | 0.9 | 🔴 BEARISH | ⚡ In 4d |

### Analysis

**MSTR**: 
- ✅ Volume 24k (high)
- ✅ OI +45% (strong buildup)
- ✅ Call accumulation (Put/Call 0.45)
- ⚠️ Beta 1.8 (volatile)
- ✅ Bullish insider
- ✅ No earnings
- **→ RANK #1**: Strong speculative whale play, high conviction

**NVDA**:
- ✅ Volume 18k (good)
- ❌ OI -8% (slightly unwinding)
- ⚪ Neutral Put/Call
- ✅ Beta 1.2 (moderate)
- ⚪ No insider signal
- ✅ No earnings
- **→ RANK #2**: Good volume, but lacking momentum (OI down)

**AAPL**:
- ⚠️ Volume 6.8k (low)
- ✅ OI +12% (small buildup)
- ⚪ Neutral Put/Call
- ✅ Beta 0.9 (stable)
- ❌ Bearish insider
- ⚠️ Earnings in 4 days (IV risk)
- **→ RANK #3** or **SKIP**: Low volume, insider bearish, earnings risk

---

## 📋 Quick Reference Checklist

When you have a 100.0 score option, check in order (top to bottom = priority):

```
☐ Volume > 10,000?           → (Most important — liquidity)
☐ VOL/OI ratio > 0.5?        → (High flow intensity, new positions)
☐ Delta 0.4 - 0.7?           → (Not too OTM, good probability)
☐ Mostly CALLs (not PUTs)?   → (Bullish sentiment)
☐ IVR > 50%?                 → (Elevated volatility context)
☐ No ⚡ earnings?            → (Avoid IV crush risk)
☐ Beta < 2.0?                → (Risk manageable)
☐ Insider BULLISH or ⚪?     → (No insider selling)

**Scoring**:
- 7+ checks → 🟢 **STRONG BUY** (high conviction)
- 5-6 checks → 🟡 **GOOD** (tradeable)
- 3-4 checks → ⚪ **NEUTRAL** (watch, don't chase)
- < 3 checks → 🔴 **SKIP**
```

---

## 📊 Practical Multi-Column Analysis

### Example Trade Analysis (From Your Screenshot)

Looking at top NVDA/AAPL/MSFT calls visible:

**NVDA $130 Call (14 DTE)**
```
Volume:    84,691 ✅ (massive, priority flow)
VOL/OI:    9.22x   ✅ (extreme — 900% of daily OI!)
Delta:     0.66    ✅ (strong bullish, 66% prob ITM)
IVR:       23.3%   🟡 (IV is compressed, low vol context)
Beta:      2.33    ⚠️ (high risk, large swings)
DTE:       14d     ✅ (sweet spot timing)

Decision: BUY (high conviction flow, ignore low IV — it's just context)
Sizing: Smaller position (high beta)
```

**AAPL $270 Call (14 DTE)**
```
Volume:    37,777  ✅ (good, 2nd tier)
VOL/OI:    5.00x   ✅ (strong, 500% of daily OI)
Delta:     0.52    ✅ (near ATM, good risk/reward)
IVR:       18.1%   🔴 (very compressed IV)
Beta:      1.11    ✅ (low beta, stable)
DTE:       14d     ✅ (sweet spot)
Insider:   BULLISH ✅ (extra confirmation)

Decision: BUY (lower risk than NVDA, good mechanics)
Sizing: Normal position
```

**MSFT $425 Call (14 DTE)**
```
Volume:    10,908  ✅ (minimum threshold met)
VOL/OI:    2.91x   ⚪ (moderate, 291% of daily OI)
Delta:     0.46    ✅ (near ATM)
IVR:       20.6%   🔴 (compressed)
Beta:      1.11    ✅ (low beta)
DTE:       14d     ✅ (sweet spot)

Decision: HOLD/WATCH (not as hot as top 2, but still valid)
Wait for better entry if others fill first
```

---

## 🔄 Daily Workflow (Sample)

### Morning (9:30 AM Market Open)
1. **Load UI** → See ~630 total opportunities
2. **Filter by Universe** → Focus on one (e.g., NASDAQ 100 = 80-90 opps)
3. **Apply filters** → `Min Vol: 10k`, `Score >= 95`
   - Result: ~30-40 candidates
4. **Sort by VOL/OI DESC** → See hottest flow first (not just volume)
5. **Spot top 10** → Quick check Delta + IV Rank + Earnings
6. **Top 3-5** → Full analysis using the checklist above

### Intraday (Every 30-45 min)
1. **Live refresh** → Prices/Greeks update every 30s
2. **Watch your positions** → Use "Vol/OI" sparkline to track momentum
3. **Re-check Top 20** → Volume changes, OI moves, insider updates

### Close / End of Day
1. **Screenshot your watchlist** → Document why you picked each
2. **Review wins/losses** → Validate which Stage 2 filters work best
3. **Update scoring signals** → Feedback for next week's improvements

---

## 📊 Data Fields Reference

| Column | What It Measures | How to Use |
|---|---|---|
| **Symbol** | Underlying ticker | Filter by sector/watchlist |
| **Side** | 📈 Call or 📉 Put | Bullish/bearish signal |
| **Strike** | Exercise price | OTM/ATM/ITM analysis |
| **Expiration** | DTE (Days to Expiration) | 5-14 DTE optimal for whales |
| **Volume** | Daily trade count | **FIRST FILTER** |
| **OI** | Open Interest | Check trend vs yesterday |
| **Whale Score** | 0-100 signal strength | 100+ = many signals present |
| **IV %** | Implied Volatility | High = expensive, avoid |
| **IV Rank** | IV percentile (0-100) | 80+ = overpriced IV |
| **Delta** | Price sensitivity | 0.3-0.7 optimal |
| **Theta** | Time decay per day | Positive = income strategy |
| **Beta** | Stock volatility vs market | < 1.3 = institutional quality |
| **Insider** | Recent insider trades | 🟢 = additional confirmation |
| **Earnings** | ⚡ within 7 days | High IV, avoid if unsure |

---

## ⚡ Pro Tips

1. **Volume is King**: Filter `Vol >= 10k` first — eliminates 70% of noise
2. **OI Momentum** beats raw OI: A 20% jump > a stable 100k OI
3. **Insider Bullish** + **Call accumulation** = highest probability plays
4. **Avoid earnings week**: Unless you specialize in IV crush plays
5. **Watch the sparkline**: Red trend = avoid, even at 100.0 score
6. **Tight spreads matter**: < 1% spread = real institutional interest
7. **Multi-signal confirmation**: 100 = many signals, not "definitely buy"

---

## 🚀 Next Actions

After picking your top 3-5 using this workflow:

1. **Execute**: Place order for 1-2 contracts
2. **Set stop**: Technical support level or -30% loss
3. **Track**: Spreadsheet with entry time, reason, exit price
4. **Validate**: Which Stage 2 filter predicted the best winners?
5. **Iterate**: Refine your Stage 2 weighting next week

---

## Questions?

**Score clustering at 100.0**: This is intentional — whale_score detects signals, not quality. Use Stage 2-4 to rank.

**Should I take ALL 100s?**: No. Stage 2 filters reduce 630 → 50-100 high quality. Stage 3 selects your top trades.

**What if OI changes tomorrow?**: That's fine. Momentum was yesterday. Check today's update every 30 min.

