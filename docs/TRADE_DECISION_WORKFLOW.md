# 🎯 Trade Decision Workflow - From Scan to Action

**Date**: May 2026  
**Status**: Current (Multi-Universe Scanning + Phase 1-3 Enrichment)  
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
- **Frequency**: Every 15 minutes during market hours (9:30 AM - 4 PM ET), Mon-Fri
- **Coverage**: 30-80 unique opportunities across 3 universes (after dedup by option_symbol)
  - NASDAQ 100: ~20-30 options
  - S&P 500: ~25-40 options
  - DOW 30: ~10-20 options
- **Output**: `data/latest_scan.json` (merged, deduplicated, sorted by whale_score DESC)
- **Enrichment**: each opportunity is enriched with 6 historical signal columns from `options_history.db`

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

### Scenario: Top results from May 14, 2026 scan

| # | Symbol | Vol | VOL/OI | MON$ | IVCRUSH | FILLVEL | CRUSHPROB | Beta | Insider | Earnings |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | NVDA $235c | 204,648 | 2.45x | ATM | LOW | LOW | 5% | 2.24 | ⚪ | ⚪ |
| 2 | AVGO $450c | 35,194 | 2.28x | OTM | LOW | LOW | 26% | — | ⚪ | ⚪ |
| 3 | TSLA $445c | 34,011 | 2.70x | ATM | LOW | LOW | 1% | 1.79 | ⚪ | ⚪ |

### Analysis

**NVDA $235 Call (DTE 1d)**:
- ✅ Volume 204k (massive — exceptional flow)
- ✅ VOL/OI 2.45x (strong flow vs open interest)
- ✅ MON$ = ATM (max gamma zone)
- ✅ IVCRUSH = LOW (IV not inflated)
- ✅ CRUSHPROB 5% (almost no crush risk)
- ⚠️ FILLVEL = LOW (but volume is huge → acceptable)
- ⚠️ DTE = 1 day (high gamma risk, size small)
- **→ RANK #1**: Institutional flow evident. Small size, manage gamma.

**TSLA $445 Call (DTE 1d)**:
- ✅ Volume 34k (strong)
- ✅ VOL/OI 2.70x (highest ratio — most intense flow)
- ✅ MON$ = ATM
- ✅ IVCRUSH = LOW
- ✅ CRUSHPROB 1% (safest of the 3)
- ✅ Beta 1.79 (manageable)
- **→ RANK #2**: Best ratio, cleanest signals, lowest crush risk.

**AVGO $450 Call (DTE 1d)**:
- ✅ Volume 35k (good)
- ✅ VOL/OI 2.28x
- 🟡 MON$ = OTM (less directional conviction)
- ✅ IVCRUSH = LOW
- ⚠️ CRUSHPROB 26% (slightly elevated vs TSLA)
- **→ RANK #3**: Good but OTM reduces conviction vs ATM peers.

---

## 📋 Quick Reference Checklist

When you have a 100.0 score option, check in order (top to bottom = priority):

```
☐ Volume > 10,000?              → (Most important — liquidity)
☐ VOL/OI ratio > 0.5?           → (High flow intensity, new positions)
☐ Delta 0.4 - 0.7?              → (Not too OTM, good probability)
☐ MON$ = ATM or ITM?            → (Avoid FAR OTM lottery tickets)
☐ IVCRUSH = LOW?                → (IV not overinflated vs history)
☐ CRUSHPROB < 40%?             → (Low post-event IV collapse risk)
☐ FILLVEL = HIGH or NORMAL?     → (Execution pace signal)
☐ ORDFLOW > 50?                 → (Bullish flow direction, if DB has history)
☐ SIZE% = TOP 25% or better?    → (Volume is above average for this contract)
☐ Mostly CALLs (not PUTs)?      → (Bullish sentiment)
☐ No ⚡ earnings?               → (Avoid IV crush risk)
☐ Beta < 2.0?                   → (Risk manageable)
☐ Insider BULLISH or ⚪?        → (No insider selling)

**Scoring**:
- 10+ checks → 🟢 **STRONG BUY** (high conviction)
- 7-9 checks  → 🟡 **GOOD** (tradeable)
- 4-6 checks  → ⚪ **NEUTRAL** (watch, don't chase)
- < 4 checks  → 🔴 **SKIP**
```

---

## 📊 Practical Multi-Column Analysis

### Example Trade Analysis (NVDA $235c, May 14, 2026)

```
Volume:      204,648 ✅ (exceptional — likely block trades)
VOL/OI:        2.45x ✅ (strong flow vs open interest)
MON$:           ATM  ✅ (max gamma zone)
IVCRUSH:        LOW  ✅ (IV not elevated vs 52w avg)
CRUSHPROB:       5%  ✅ (no IV crush risk)
FILLVEL:        LOW  ⚠️  (slow fill velocity, but volume compensates)
ORDFLOW:         LO  ⚪ (neutral — DB still accumulating per-contract history)
SIZE%:          25%  ⚪ (DB still building 30d history → will improve)
Delta:          0.17 ⚠️ (low — OTM, high leverage play)
DTE:              1d ⚠️ (1 day = high gamma, size small!)
Beta:           2.24 ⚠️ (volatile — reduce size)

Decision: BUY small (exceptional flow, manage 1-day gamma aggressively)
Sizing: 1-2 contracts max
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
| **Money** | Moneyness bar + label | See MON$ column below |
| **Volume** | Daily trade count | **FIRST FILTER** |
| **OI** | Open Interest | Check trend vs yesterday |
| **VOL/OI** | Flow intensity ratio | > 1.0 = extreme activity |
| **Delta** | Price sensitivity | 0.3-0.7 optimal |
| **Sizzle** | Vol/OI anomaly signal | Spikes = unusual flow |
| **V5D** | 5-day volume trend | Trend direction |
| **IV%** | Implied Volatility | High = expensive, avoid |
| **IVR** | IV Rank (0-100%) | 80+ = overpriced IV |
| **Chg%** | Price change % | Context |
| **Stk Vol** | Underlying stock volume | Confirms direction |
| **Sector** | Industry sector | Sector rotation context |
| **Beta** | Stock volatility vs market | < 1.3 = institutional quality |
| **Insider** | Recent insider trades (30d) | 🟢 = additional confirmation |
| **⚡** | Earnings within 7 days | High IV, avoid if unsure |
| **MON$** | Moneyness quality badge | ITM/ATM/OTM — see below |
| **SIZE%** | Size percentile vs 30d avg | > TOP 5% = unusual volume |
| **IVCRUSH** | IV crush risk | LOW/HIGH vs 52w avg |
| **FILLVEL** | Fill velocity | HIGH = institutional execution speed |
| **ORDFLOW** | Order flow strength (0-100) | > 70 = strong bullish conviction |
| **CRUSHPROB** | Probability of IV crush (%) | > 50% = dangerous if holding through event |
| **Score** | Whale Score 0-100+ | 100 = many signals, use Stage 2 to rank |

---

## 🧪 Phase 1-3 Signal Columns — Detailed Guide

These 6 columns are computed from `options_history.db` (historical scan data). They become more accurate as the DB accumulates daily scans.

### MON$ — Moneyness Quality

| Badge | Condition | Meaning | Score Impact |
|---|---|---|---|
| `ITM` 🟢 | Stock price > Strike (calls) | In-the-money, directional | +1% |
| `ATM` 🔵 | Within ~2% of strike | Max gamma zone, most liquid | +3% |
| `OTM` 🟡 | Slightly out of money | High leverage, less prob | — |
| `FAR` 🔴 | > 10% OTM | Lottery ticket | -15% |

**Rule**: Prefer `ATM` or `ITM` for institutional plays. `FAR` = avoid unless very high volume.

---

### SIZE% — Volume Size Percentile (30-Day)

| Badge | Condition | Meaning |
|---|---|---|
| `TOP 1%` 🟢🟢 | Today's vol > 3× 30d avg | Exceptional — block trade likely |
| `TOP 5%` 🟢 | Today's vol > 2× 30d avg | Strong unusual activity |
| `TOP 25%` 🟡 | Today's vol > 1.3× 30d avg | Above normal |
| `25%` ⚪ | Today's vol ≈ 30d avg | Normal activity |

> **Note**: Currently shows `25%` for most contracts as DB is still building 30-day history. Will become meaningful after ~30 days of scans.

---

### IVCRUSH — IV Crush Risk

| Badge | IV Ratio | Meaning |
|---|---|---|
| `LOW` 🟢 | current_IV < 52w avg | IV is compressed, safe to buy premium |
| `NORMAL` 🟡 | 1.0 – 1.5× avg | Normal conditions |
| `HIGH` 🔴 | current_IV > 1.5× avg | IV inflated — risk of crash post-event |

**Rule**: Avoid `HIGH` unless you're playing the event itself. Perfect short premium setup.

---

### FILLVEL — Fill Velocity

| Badge | Contracts/min | Meaning |
|---|---|---|
| `HIGH` 🟢 | > 500/min | Fast institutional execution |
| `NORMAL` 🟡 | 100–500/min | Mixed |
| `LOW` ⚪ | < 100/min | Slow retail flow |

Calculated as `SUM(daily_volume) / 390 minutes`. Higher = faster fill pressure = urgency.

---

### ORDFLOW — Order Flow Strength (0–100)

| Value | Badge | Meaning |
|---|---|---|
| 70–100 | `BULL` 🟢 | Strong bullish pressure trend over 30d |
| 50–70 | `LO` 🟡 | Slightly bullish / neutral |
| 30–50 | `BEAR` 🔴 | Bearish pressure |
| = 50 | `LO` ⚪ | Neutral — insufficient per-contract history |

> **Note**: Requires ≥3 scans of the **same option contract** to be meaningful. Long-dated options will accumulate this over weeks.

---

### CRUSHPROB — IV Crush Probability (%)

| Value | Meaning | Action |
|---|---|---|
| > 70% | Very high crush risk | Sell premium / avoid buying IV |
| 30–70% | Moderate risk | Monitor if near earnings |
| < 30% | Low risk | Safe to buy options premium |

Combines IV dispersion across strikes + IV/52w ratio + earnings catalyst.

---

---

## ⚡ Pro Tips

1. **Volume is King**: Filter `Vol >= 10k` first — eliminates most noise
2. **MON$ ATM = best gamma**: ATM options have max sensitivity to price moves
3. **IVCRUSH LOW + CRUSHPROB < 30%** = safe to buy premium (no overpriced IV)
4. **ORDFLOW > 70** (when DB has history) = sustained institutional buying pressure
5. **SIZE% TOP 5%** = this specific contract is getting unusually large attention today
6. **Avoid FILLVEL LOW + CRUSHPROB HIGH** combo — slow execution into inflated IV
7. **Watch the sparkline** in ORDFLOW column: trend direction > single data point
8. **DTE 1-3d**: Extremely high gamma — use tiny size, expect large swings
9. **DTE 7-21d**: Sweet spot for whale flow — best risk/reward ratio
10. **Multi-signal confirmation**: 100 = many signals, not "definitely buy"

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

**Should I take ALL 100s?**: No. Stage 2 filters reduce to ~10-20 high quality. Stage 3 selects your top trades.

**What if ORDFLOW shows LO for everything?**: Normal — requires ≥3 scans of the same contract. Will improve as DB builds daily history.

**SIZE% shows 25% for everything?**: Expected while DB accumulates 30-day history. Will differentiate after ~30 trading days.

**CRUSHPROB > 50% but earnings not flagged?**: High IV dispersion across strikes — the market is pricing in a big move even without a scheduled catalyst. Treat like an earnings play.

