# 📚 Documentation Index

## 🚀 Start Here

### New to Option Finder?
1. [TRADE_DECISION_WORKFLOW.md](TRADE_DECISION_WORKFLOW.md) ⭐ **START HERE**
   - How to use scan results to make trading decisions
   - Multi-stage filtering to differentiate 100/100 scores
   - Practical trade examples and decision trees

2. [AI_SETUP_GUIDE.md](AI_SETUP_GUIDE.md)
   - Get the system running locally or on a VM
   - Environment configuration

---

## 🏗️ Architecture & Integrations

### System Design
- [HYBRID_ARCHITECTURE.md](HYBRID_ARCHITECTURE.md) — Tradier + Polygon.io data fusion
- [DOCKER_SETUP.md](DOCKER_SETUP.md) — GitHub Actions Docker optimization
- [PIPELINE_DEFINITION.md](PIPELINE_DEFINITION.md) — End-to-end scanning pipeline

### Data Sources & APIs
- [MARKET_CHAMELEON_INTEGRATION.md](MARKET_CHAMELEON_INTEGRATION.md) — Historical IV data
- [HISTORICAL_VOLUME_ANALYSIS.md](HISTORICAL_VOLUME_ANALYSIS.md) — Volume metrics

---

## 🐋 Features & Signals

### Short Interest Screening
- [SHORT_INTEREST_FEATURE.md](SHORT_INTEREST_FEATURE.md) — High SI stock detection + filtering
- [SHORT_INTEREST_QUICK_START.md](SHORT_INTEREST_QUICK_START.md) — Get started with SI screening
- [SHORT_INTEREST_UI_INTEGRATION_TEST.md](SHORT_INTEREST_UI_INTEGRATION_TEST.md) — UI integration details
- [SHORT_INTEREST_INPUT_ANALYSIS.md](SHORT_INTEREST_INPUT_ANALYSIS.md) — Input validation & analysis

### Order Flow & Whale Signals
See [TRADE_DECISION_WORKFLOW.md](TRADE_DECISION_WORKFLOW.md) Stage 2-3 for signal explanations:
- Put/Call Flow Ratio (bullish/bearish sentiment)
- OI Momentum (new positioning detection)
- Block Trade Detection (volume + tight spreads)
- Spread Compression (institutional liquidity)

---

## 📊 Quick Start Guides

- [QUICK_START_SHORT_INTEREST.md](QUICK_START_SHORT_INTEREST.md) — Run your first SI scan
- [WORKFLOW_IMPROVEMENTS.md](WORKFLOW_IMPROVEMENTS.md) — Recent improvements & changes

---

## 📦 Archive

Outdated documentation moved to `legacy_archive/docs_archive/`:
- Old VM setup guides (replaced by GitHub Actions)
- Old Streamlit UI docs (replaced by FastAPI)
- Old implementation notes (superseded)
- Old cleanup/planning docs

See [legacy_archive/docs_archive/README.md](../legacy_archive/docs_archive/README.md) for full list.

---

## Current System Status (April 2026)

✅ **Active Components:**
- Multi-universe parallel scanning (NASDAQ100, S&P500, DOW30)
- 630 opportunities per scan (~7x historical improvement)
- FastAPI backend with WebSocket live updates
- GitHub Actions automation (15-min intervals)
- Docker optimization for CI/CD
- Client-side universe filtering (no re-scans needed)
- History database with OI momentum + IV rank tracking
- Order flow signals (Put/Call ratio + OI momentum)
- Insider trading sentiment (Finviz integration)
- Short interest screening (highshortinterest.com)

✅ **Scoring Signals:**
- Big Call Buying (volume)
- High Short Interest (SI%)
- Block Trades (100+ contracts)
- Tight Spreads (< 0.5% = +7.4 points)
- OI Momentum (+3 for +30% OI change)
- Put/Call Flow Ratio (+2 for call accumulation)
- IV Rank / Volume Trends
- Insider Sentiment

---

## How to Use This Documentation

**I want to trade — what do I do?**
→ Start with [TRADE_DECISION_WORKFLOW.md](TRADE_DECISION_WORKFLOW.md)

**I want to understand the system architecture**
→ Read [HYBRID_ARCHITECTURE.md](HYBRID_ARCHITECTURE.md) + [DOCKER_SETUP.md](DOCKER_SETUP.md)

**I want to use short interest screening**
→ Read [SHORT_INTEREST_FEATURE.md](SHORT_INTEREST_FEATURE.md) + [SHORT_INTEREST_QUICK_START.md](SHORT_INTEREST_QUICK_START.md)

**I want to add a new feature**
→ Read system docs first, then check [PIPELINE_DEFINITION.md](PIPELINE_DEFINITION.md)

**I'm debugging something**
→ Check the specific feature doc + [WORKFLOW_IMPROVEMENTS.md](WORKFLOW_IMPROVEMENTS.md) for recent changes

---

**Last Updated**: April 19, 2026  
**System Status**: ✅ Production Ready  
**Next Review**: After first full week of multi-universe scanning

