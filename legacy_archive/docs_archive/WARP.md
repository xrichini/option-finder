# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

A Streamlit-based options whale screener that detects "Big Call/Put Buying" patterns by analyzing options volume, open interest, and combining with high short interest data from highshortinterest.com. The application uses the Tradier API for real-time options data and implements a proprietary "Whale Score" algorithm.

## Environment Setup

### Virtual Environment & Dependencies
```bash
# Activate virtual environment (Windows)
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with API keys:
# TRADIER_API_KEY=your_tradier_api_key
# OPENAI_API_KEY=your_openai_key (optional)
# PERPLEXITY_API_KEY=your_perplexity_key (optional)
```

### Running the Application
```bash
# Run the main Streamlit application
streamlit run main.py

# For debugging with VSCode, use the configured launch profile "Python: Streamlit"

# Demo the new progress interface
streamlit run demo_progress.py

# Demo the new real-time scanning system
streamlit run demo_scanning.py

# Demo the improved user workflow
streamlit run demo_workflow.py
```

## Testing

### Run Tests
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_helpers.py

# Run async performance tests
pytest tests/test_async_performance.py -v

# Run a single test function
pytest tests/test_helpers.py::test_get_high_short_interest_symbols_success

# Run performance tests (requires valid API key)
python tests/test_performance.py

# Run tests with async support
pytest tests/ -v --asyncio-mode=auto
```

### Test Structure
- `conftest.py`: Test configuration and Python path setup
- `test_helpers.py`: Tests for utility functions, especially web scraping functionality with mocking
- `test_async_performance.py`: Comprehensive tests for async operations, caching, and performance optimizations
- `test_performance.py`: Integration performance testing script (requires API key)

### Test Categories
**Unit Tests**: Test individual components with mocks
- Cache expiration logic
- Whale score calculations
- Option data processing
- Market data filtering

**Integration Tests**: Test component interactions
- Async batch processing performance
- Progress callback functionality
- Rate limiting effectiveness

**Performance Tests**: Validate optimization effectiveness
- Pre-filtering API call reduction
- Caching speedup measurements
- Async vs sequential processing comparison

## Code Architecture

### Core Components

**Data Layer (`data/`)**
- `tradier_client.py`: Synchronous Tradier API client for options data retrieval
- `async_tradier.py`: Asynchronous version with caching for symbol filtering
- `screener_logic.py`: Core screening algorithm and whale score calculation

**Models (`models/`)**
- `option_model.py`: `OptionScreenerResult` dataclass with computed properties for ratios

**UI Layer (`ui/`)**
- `dashboard.py`: Main Streamlit dashboard with tabs for calls/puts, sidebar configuration

**Utilities (`utils/`)**
- `config.py`: Centralized configuration using Streamlit secrets
- `helpers.py`: Web scraping for highshortinterest.com, number formatting, and async utilities

### Key Algorithms

**Whale Score Calculation** (0-100 scale):
- Volume 1D: 0-25 points (thresholds: 500, 1K, 2K, 5K+)
- Volume 7D: 0-25 points (thresholds: 5K, 10K, 20K+)
- Volume/OI Ratio: 0-25 points (thresholds: 1x, 2x, 3x, 5x+)
- Delta Score: 0-15 points (for ITM/ATM options)
- IV Score: 0-10 points (implied volatility premium)

**Options Screening Flow**:
1. Filter symbols by DTE (Days to Expiration)
2. Retrieve option chains with Greeks
3. Apply volume, open interest, and whale score thresholds
4. Calculate and display results in sortable tables

### API Integration

**Tradier API Endpoints Used**:
- `/markets/options/expirations` - Get available expiration dates
- `/markets/options/chains` - Retrieve options chains with Greeks
- `/markets/quotes` - Get current quotes for symbols

**External Data Sources**:
- highshortinterest.com - Web scraping for high short interest symbols
- BeautifulSoup parsing with error handling and user-agent headers

### Configuration Management

All configurable parameters are centralized in `Config` class:
- `DEFAULT_DTE = 7` - Default days to expiration
- `MIN_VOLUME_THRESHOLD = 1000` - Minimum volume filter
- `MIN_OPEN_INTEREST_THRESHOLD = 1000` - Minimum OI filter
- `MIN_WHALE_SCORE = 70` - Minimum score for whale detection

### Session State Management

Streamlit session state tracks:
- Symbol lists (raw and filtered for optionability)
- Scanner parameters (DTE, volume, OI thresholds)
- Active tab state
- API configuration status

## Development Notes

### Async Handling
The project uses `nest_asyncio` to enable asyncio within Streamlit's event loop, particularly for:
- Batch symbol validation against Tradier API
- Concurrent options data retrieval
- Web scraping with proper timeout handling

### Error Handling Patterns
- Try-catch blocks with user-friendly error messages in Streamlit UI
- Fallback values for missing Greeks data (delta=0.3, iv=0.4)
- Graceful degradation when API calls fail

### Performance Optimizations
- `@st.cache_data` decorators for expensive API calls
- Symbol optionability caching to avoid repeated API calls
- Batch processing of symbol validation

### Code Style
- Uses Black formatter (configured in VSCode settings)
- Pylint enabled for linting
- French comments and UI text (but English variable/function names)

## Performance Optimizations

### Smart Pre-filtering
**Before expensive Tradier API calls**, the app filters symbols using yfinance:
- Market capitalization threshold (default: $100M+)
- Average volume threshold (default: 500K+)
- Sector exclusions (REITs, Asset Management)
- **Result**: Reduces API calls by 40-60% typically

### Enhanced Async & Caching
**AsyncTradierClient improvements**:
- Rate limiting with semaphores (10 concurrent, 0.1s between requests)
- Persistent disk caching with TTL (1hr for optionable data, 30min for market data)
- Batch processing with proper error handling
- Session management with connection pooling

**Caching Strategy**:
- `data/.cache/optionable_cache.json` - Persistent optionable symbol cache
- `@st.cache_data` for market data (30min TTL)
- Instance-level memory caching with expiration

### High-Volume Ticker Optimization
**For 100+ symbols**:
1. **Pre-filter** using market criteria (saves ~50% API calls)
2. **Batch process** in groups of 20 symbols
3. **Cache results** persistently across sessions
4. **Progress tracking** with timeout handling (60s per batch)
5. **Async screening** with proper resource cleanup

### Performance Testing
```bash
# Test all optimizations
python test_performance.py

# Expected improvements:
# - Pre-filtering: 40-60% API call reduction
# - Caching: 3-10x speedup on repeated queries
# - Async processing: 2-5x speedup vs sequential
```

### Configuration
All performance parameters configurable in `utils/config.py`:
- `MAX_CONCURRENT_REQUESTS = 10`
- `API_RATE_LIMIT = 0.1` 
- `BATCH_SIZE_SYMBOLS = 20`
- `MIN_MARKET_CAP = 100_000_000`
- `CACHE_TTL_OPTIONABLE = 3600`

## Enhanced User Interface

### Real-Time Progress Tracking
**Problem Solved**: Previously, the interface would freeze during screening with only console output visible.

**New Features**:
- **Dynamic Progress Bar**: Visual percentage completion indicator
- **Live Metrics**: Real-time updates for symbols processed, options found, elapsed time
- **Detailed Feedback**: Step-by-step progress in expandable details section
- **Interruption Control**: Stop button to cancel long-running scans
- **Smart Throttling**: UI updates limited to 500ms intervals to prevent flickering

### Progress Interface Components
```python
# Main progress elements
main_progress = st.progress(0)           # Progress bar
status_text = st.empty()                 # Current status
symbols_container = st.empty()           # Symbols analyzed counter
options_container = st.empty()           # Options found counter
time_container = st.empty()              # Elapsed time
details_text = st.empty()                # Detailed feedback
```

### Smart Symbol Loading
**UI Enhancement**: New "🤖 Charger symboles (Smart)" button with:
- Pre-filtering options in sidebar
- Market cap and volume thresholds
- Sector exclusion controls
- Progress feedback during loading

### Scan Interruption
Users can stop long-running scans using the "🛑 Interrompre le scan" button, which:
- Sets `st.session_state.stop_scanning = True`
- Gracefully exits the screening loop
- Preserves partial results
- Provides clear feedback about interruption

### Real-Time Scanning System
**Architecture Solution**: Chunked processing with `st.rerun()` for live UI updates

**Chunking Strategy**:
```python
# Session state management for progressive scanning
st.session_state.is_scanning = True
st.session_state.symbols_to_scan = symbols
st.session_state.current_scan_index = 0
st.session_state.scan_results = []

# Process one symbol per rerun cycle
def _render_scanning_progress(option_type):
    current_index = st.session_state.current_scan_index
    if current_index < len(symbols):
        # Process single symbol with real-time feedback
        results = self._process_single_symbol(symbols[current_index])
        st.session_state.current_scan_index += 1
        st.rerun()  # Trigger next iteration
```

**Key Benefits**:
- **Live Progress Updates**: UI refreshes after each symbol
- **Responsive Interface**: User can interact during processing
- **Granular Control**: Stop/resume functionality
- **Detailed Feedback**: Step-by-step analysis visibility
- **Memory Efficient**: Processes symbols individually

### User Workflow Optimization
**Problem Solved**: Confusing workflow with global scanner button and non-persistent results

**Enhanced User Experience**:
```
1. Load Symbols (Smart Pre-filtering)
   ↓
2. Navigate to "Calls" tab → Click "Scanner Calls"
   ↓  
3. Navigate to "Puts" tab → Click "Scanner Puts"
   ↓
4. Compare results between tabs (data persists)
   ↓
5. Clear selectively or globally as needed
```

**Key Improvements**:
- **Contextual Controls**: Each tab has its own Scanner and Clear buttons
- **Result Persistence**: Calls results remain visible when viewing Puts tab
- **Stop Button Fix**: Proper cleanup prevents automatic restart after interruption
- **Intuitive Flow**: Clear separation of concerns per option type

**UI Changes**:
- Removed global "SCANNER" button from sidebar
- Added contextual "🔄 Scanner Calls/Puts" buttons in each tab
- Added "🧹 Clear Calls/Puts" buttons for selective cleanup
- Maintained "🧹 Clear All Results" in sidebar for global cleanup
