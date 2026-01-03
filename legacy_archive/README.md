# 📦 Legacy Code Archive

This directory contains deprecated code from the **Streamlit to FastAPI migration**.

## Files Archived

### Screening Logic (Replaced by `/services/`)
- **screener_logic.py** (628 LOC)
  - Old base screening implementation
  - Replaced by: `services/screening_service.py`
  
- **enhanced_screener.py** (206 LOC)
  - Streamlit-specific wrapper
  - Replaced by: FastAPI endpoints in `api/`
  
- **enhanced_screener_v2.py** (565 LOC)
  - Experimental enhancement attempt
  - Replaced by: `services/hybrid_screening_service.py`

### UI Components (Removed)
- **dashboard.py** (54K)
  - Old Streamlit dashboard
  - Replaced by: `ui/index.html` + FastAPI in `app.py`

### Data Handling (Replaced by `/services/`)
- **async_tradier.py** (12K)
  - Async wrapper for Tradier
  - Replaced by: `data/enhanced_tradier_client.py`
  
- **historical_data_manager.py** (12K)
  - Manual data fetching
  - Replaced by: `services/hybrid_data_service.py`

## Statistics

**Total archived: 1,477 LOC**

- Screener logic: 1,399 LOC
- UI: 54K
- Data: 24K

## Purpose

These files are kept for reference in case:
1. Legacy Streamlit app needs to be restored
2. Tests reference old implementations
3. Performance comparison with new code

## When to Delete

Safe to delete after:
- ✅ All tests pass with new code paths
- ✅ Streamlit app is no longer needed
- ✅ No reference docs mention these files

## Current Status

**Production**: Not used ✅
**Tests**: May reference (run tests to verify)
**UI**: Fully replaced by FastAPI + HTML/JS ✅

---

**Archived on**: 2026-01-03
**Migration**: Streamlit → FastAPI completed
**Status**: Legacy code preserved for reference
