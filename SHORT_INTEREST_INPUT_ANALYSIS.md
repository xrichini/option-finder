# Short Interest Pipeline - Input Parameters Analysis

## Status: ✅ ACTIVE (Not Unused)

The Streamlit legacy parameters **ARE actively used** in the FastAPI architecture for the Short Interest input pipeline.

---

## 📍 Where Parameters Are Used

### 1. **HTML Frontend** (ui/index.html)
The sidebar contains dedicated Short Interest input controls:

```html
<!-- Exchange Selection -->
<select id="sidebarExchange">
    <option value="nasdaq" selected>NASDAQ</option>
    <option value="nyse">NYSE</option>
    <option value="amex">AMEX</option>
    <option value="all">All Markets</option>
</select>

<!-- Short Interest Minimum -->
<input type="number" id="sidebarMinShortInterest" value="20" min="5" max="100">

<!-- Market Cap Minimum -->
<select id="sidebarMinMarketCap">
    <option value="50000000">50M $</option>
    <option value="100000000" selected>100M $</option>
    <option value="500000000">500M $</option>
    <option value="1000000000">1B $</option>
    <option value="5000000000">5B $</option>
</select>

<!-- Stock Volume Minimum -->
<select id="sidebarMinStockVolume">
    <option value="100000">100K</option>
    <option value="500000" selected>500K</option>
    <option value="1000000">1M</option>
    <option value="2000000">2M</option>
</select>
```

**Location**: Lines 790-860 in ui/index.html

---

### 2. **JavaScript Functions** (ui/index.html)

#### Function: `loadShortInterestSymbolsAutomatically()` (Lines 2186-2240)
**Purpose**: Auto-load symbols when checkbox is enabled

```javascript
const exchange = document.getElementById('sidebarExchange').value;
const minMarketCap = document.getElementById('sidebarMinMarketCap').value;
const minStockVolume = document.getElementById('sidebarMinStockVolume').value;
const minShortInterest = document.getElementById('sidebarMinShortInterest').value;

const params = new URLSearchParams({
    exchange: exchange,
    min_market_cap: minMarketCap,
    min_avg_volume: minStockVolume,
    min_short_interest: minShortInterest,
    enable_prefiltering: 'true'
});

const response = await fetch(`${API_BASE}/api/short-interest/symbols?${params}`);
```

#### Function: `loadShortInterestSymbols()` (Lines 2366-2430)
**Purpose**: Main pipeline - Short Interest → Options Screening

This function:
1. Reads all 4 parameters from HTML inputs
2. Calls `/api/short-interest/symbols` endpoint
3. Retrieves filtered symbols
4. Passes them to options screening

---

### 3. **API Endpoints** (api/short_interest_endpoints.py)

#### GET `/api/short-interest/symbols` (Lines 176-220)
**Query Parameters** (directly from HTML):
- `exchange` (string) - "all", "nasdaq", "nyse", "amex"
- `min_market_cap` (int) - Minimum market cap in USD
- `min_avg_volume` (int) - Minimum average daily volume
- `min_short_interest` (float) - Minimum SI percentage
- `enable_prefiltering` (bool) - Whether to apply filters

**Flow**:
```python
def get_short_interest_symbols(
    exchange: str = Query(default="all"),
    enable_prefiltering: bool = Query(default=True),
    min_market_cap: int = Query(default=100_000_000),
    min_avg_volume: int = Query(default=500_000),
    # ... calls scraper with these exact parameters
)
```

**Response**: List of filtered symbols
```json
{
    "success": true,
    "symbols": ["SYMBOL1", "SYMBOL2", ...],
    "count": 42,
    "execution_time_seconds": 8.5
}
```

#### GET `/api/short-interest/stocks` (Lines 75-174)
**Query Parameters**: Same 4 parameters + `max_price`

**Response**: Full stock data with all SI metrics
```json
{
    "stocks": [
        {
            "symbol": "AAPL",
            "short_interest_pct": 25.4,
            "market_cap": 2700000000,
            "sector": "Technology",
            ...
        }
    ],
    "total_count": 250,
    "filtered_count": 42
}
```

#### POST `/api/short-interest/scan` (Lines 223-331)
**Purpose**: Full pipeline execution - SI → Filter → Options Screening

**Request Body**:
```python
class SymbolsRequest(BaseModel):
    exchange: str = "all"
    enable_prefiltering: bool = True
    min_market_cap: int = 100_000_000
    min_avg_volume: int = 500_000
```

**Flow**:
1. Get SI symbols with filters
2. Enrich with market data (yfinance)
3. Apply market cap / volume filters
4. Screen options on filtered symbols
5. Return opportunities with whale scores

---

## 🔄 Data Flow: Complete Pipeline

```
HTML Inputs (User selects filters)
    ↓
JavaScript reads 4 parameters
    ↓
/api/short-interest/symbols?exchange=NASDAQ&min_market_cap=100M&...
    ↓
short_interest_endpoints.py - get_short_interest_symbols()
    ↓
ShortInterestScraper.scrape_short_interest_stocks(exchange)
    ↓
ShortInterestScraper.enrich_with_market_data(stocks)  [yfinance]
    ↓
ShortInterestScraper.filter_stocks_by_criteria(stocks, params)
    ↓
Returns: ["AAPL", "TSLA", ...]
    ↓
JavaScript launches screening on filtered symbols
    ↓
/api/hybrid/scan-all [POST with symbols]
    ↓
Options screening + whale score calculation
    ↓
Results displayed in UI
```

---

## 📋 Parameter Usage Mapping

| Parameter | HTML Input | API Param | Scraper Method | Default |
|-----------|-----------|-----------|----------------|---------|
| Exchange | `sidebarExchange` select | `exchange` | `scrape_short_interest_stocks()` | "nasdaq" |
| Min Short Interest | `sidebarMinShortInterest` number | `min_short_interest` | `filter_stocks_by_criteria()` | 20% |
| Min Market Cap | `sidebarMinMarketCap` select | `min_market_cap` | `filter_stocks_by_criteria()` | 100M |
| Min Volume | `sidebarMinStockVolume` select | `min_avg_volume` | `filter_stocks_by_criteria()` | 500K |

---

## 🔍 How Parameters Are Applied

### 1. **Exchange Filter** - Scraping Level
```python
# In short_interest_scraper.py
def scrape_short_interest_stocks(self, exchange: str = "all"):
    url = self.base_url
    if exchange.lower() != "all":
        url += f"?exchange={exchange.lower()}"
    # Scrapes HighShortInterest.com with exchange filter
```

### 2. **Market Cap Filter** - Post-Processing
```python
# In filter_stocks_by_criteria()
if stock.market_cap and stock.market_cap < params.min_market_cap:
    continue  # Skip stocks below threshold
```

### 3. **Volume Filter** - Post-Processing
```python
# In filter_stocks_by_criteria()
if stock.avg_volume and stock.avg_volume < params.min_avg_volume:
    continue  # Skip low-volume stocks
```

### 4. **Short Interest Filter** - Post-Processing
```python
# In filter_stocks_by_criteria()
if stock.short_interest_pct < params.min_short_interest:
    continue  # Skip low SI stocks
```

---

## ✨ User Experience Flow

1. **User opens UI** → Sidebar shows default filters:
   - Exchange: NASDAQ
   - Min Short Interest: 20%
   - Min Market Cap: 100M
   - Min Volume: 500K

2. **User adjusts filters** → Clicks "Short Interest → Options" button

3. **System executes pipeline**:
   - Scrapes HighShortInterest.com for NASDAQ stocks
   - Enriches with yfinance market data
   - Filters by SI ≥ 20%, Market Cap ≥ 100M, Volume ≥ 500K
   - Screens options on resulting symbols
   - Displays opportunities

4. **Results show** with whale scores, IV, volume, etc.

---

## 🎯 Current Status: FULLY ACTIVE

✅ **HTML Inputs**: Present and functional (lines 790-860)  
✅ **JavaScript Functions**: Reading inputs and calling APIs (lines 2186-2430)  
✅ **API Endpoints**: Accepting and using parameters (short_interest_endpoints.py)  
✅ **Data Processing**: Filtering applied correctly in scraper (short_interest_scraper.py)  
✅ **Pipeline**: End-to-end working for user input

---

## 📌 Notes

- These parameters are **NOT unused legacy code**
- They are part of the **active Short Interest feature pipeline**
- The UI controls match the API parameters exactly
- Default values (20%, 100M, 500K) match production scraper defaults
- The pipeline is complete and functional

---

## 🚀 Integration Opportunity

**Status**: Ready for expansion

The short interest scraper already supports:
- Manual ticker input (text area)
- Automatic scraping with filters
- Market data enrichment
- Filtering by multiple criteria

**Next Phase**: Could integrate:
- User-saved filter presets
- Scheduled scraping
- Alert system for new opportunities
- Historical tracking of SI changes

