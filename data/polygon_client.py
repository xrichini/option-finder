# polygon_client.py - Client optimisé pour Polygon.io API selon la documentation officielle
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
import time

@dataclass
class StockBar:
    """Structure pour les données de barres actions"""
    ticker: str
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: float
    transactions: int

@dataclass
class OptionContract:
    """Structure pour les contrats d'options"""
    ticker: str
    underlying_ticker: str
    contract_type: str  # 'call' or 'put'
    strike_price: float
    expiration_date: str
    exercise_style: str
    shares_per_contract: int
    
@dataclass
class OptionQuote:
    """Structure pour les quotes d'options"""
    ticker: str
    bid: float
    ask: float
    bid_size: int
    ask_size: int
    last_quote_timestamp: int
    implied_volatility: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None

@dataclass
class OptionTrade:
    """Structure pour les trades d'options"""
    ticker: str
    timestamp: int
    price: float
    size: int
    exchange: int
    sip_timestamp: int

class PolygonClient:
    """Client optimisé pour Polygon.io API selon la documentation officielle"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.polygon.io"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        
        # Rate limiting pour free tier (5 requests/minute)
        self.request_delay = 12  # 12 seconds between requests for free tier
        self.last_request_time = 0
        
        # Configure session headers
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'User-Agent': 'squeeze-finder/1.0'
        })
        
        print(f"🔗 Polygon.io client initialized (API: {api_key[:8]}...{api_key[-4:]})")
    
    def validate_key(self) -> bool:
        """Validate the API key by making a simple request"""
        try:
            # Try to get a simple market status endpoint (minimal data usage)
            response = self.session.get(
                f"{self.base_url}/v1/marketstatus/now",
                params={'apikey': self.api_key},
                timeout=10
            )
            
            if response.status_code == 401:
                print("❌ Polygon API Key Invalid (401 Unauthorized)")
                return False
            elif response.status_code == 403:
                print("❌ Polygon API Access Forbidden (403)")
                return False
            elif response.status_code == 200:
                print("✅ Polygon API Key Valid")
                return True
            else:
                print(f"⚠️ Polygon API returned status {response.status_code}")
                return response.status_code not in [401, 403]
                
        except Exception as e:
            print(f"❌ Error validating Polygon key: {e}")
            return False
    
    def _rate_limit(self):
        """Apply rate limiting for free tier"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.request_delay:
            sleep_time = self.request_delay - elapsed
            print(f"⏱️ Rate limiting: waiting {sleep_time:.1f}s...")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make a rate-limited API request"""
        self._rate_limit()
        
        if params is None:
            params = {}
        
        params['apikey'] = self.api_key
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') != 'OK':
                print(f"⚠️ API Warning: {data.get('status')} - {data.get('error', 'Unknown error')}")
            
            return data
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                print("❌ Rate limit exceeded. Consider upgrading your Polygon.io plan.")
            elif response.status_code == 401:
                print("❌ Authentication failed - Invalid Polygon.io API key")
                raise ValueError("Invalid Polygon API key (401 Unauthorized)")
            elif response.status_code == 403:
                print("❌ Access forbidden - Check Polygon.io plan permissions")
                raise ValueError("Polygon API access forbidden (403)")
            raise e
        except Exception as e:
            print(f"❌ Request failed: {e}")
            raise e
    
    # STOCKS API METHODS
    def get_stock_aggregates(self, 
                           ticker: str, 
                           multiplier: int = 1,
                           timespan: str = "day",
                           from_date: Union[str, datetime] = None,
                           to_date: Union[str, datetime] = None,
                           limit: int = 5000) -> List[StockBar]:
        """
        Get aggregate bars for stocks
        Ref: https://polygon.io/docs/stocks/get_v2_aggs_ticker__stocksticker__range__multiplier___timespan___from___to
        """
        
        if from_date is None:
            from_date = datetime.now() - timedelta(days=30)
        if to_date is None:
            to_date = datetime.now()
        
        # Convert dates to strings if needed
        if isinstance(from_date, datetime):
            from_date = from_date.strftime('%Y-%m-%d')
        if isinstance(to_date, datetime):
            to_date = to_date.strftime('%Y-%m-%d')
        
        endpoint = f"/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
        params = {
            'adjusted': 'true',
            'sort': 'asc',
            'limit': limit
        }
        
        print(f"📊 Fetching stock aggregates for {ticker} ({from_date} to {to_date})")
        
        data = self._make_request(endpoint, params)
        
        results = data.get('results', [])
        
        stock_bars = []
        for result in results:
            bar = StockBar(
                ticker=ticker,
                timestamp=result.get('t', 0),
                open=result.get('o', 0),
                high=result.get('h', 0),
                low=result.get('l', 0),
                close=result.get('c', 0),
                volume=result.get('v', 0),
                vwap=result.get('vw', 0),
                transactions=result.get('n', 0)
            )
            stock_bars.append(bar)
        
        print(f"✅ Retrieved {len(stock_bars)} stock bars for {ticker}")
        return stock_bars
    
    def get_market_status(self) -> Dict:
        """Get current market status"""
        endpoint = "/v1/marketstatus/now"
        
        data = self._make_request(endpoint)
        
        return {
            'market': data.get('market', 'unknown'),
            'serverTime': data.get('serverTime', ''),
            'exchanges': data.get('exchanges', {}),
            'currencies': data.get('currencies', {})
        }
    
    # OPTIONS API METHODS
    def get_option_contracts(self, 
                           underlying_ticker: str,
                           contract_type: Optional[str] = None,
                           expiration_date: Optional[str] = None,
                           strike_price: Optional[float] = None,
                           limit: int = 1000) -> List[OptionContract]:
        """
        Get option contracts for an underlying asset
        Ref: https://polygon.io/docs/options/get_v3_reference_options_contracts
        """
        
        endpoint = "/v3/reference/options/contracts"
        params = {
            'underlying_ticker': underlying_ticker,
            'limit': limit,
            'sort': 'expiration_date'
        }
        
        if contract_type:
            params['contract_type'] = contract_type
        if expiration_date:
            params['expiration_date'] = expiration_date
        if strike_price:
            params['strike_price'] = strike_price
        
        print(f"📋 Fetching option contracts for {underlying_ticker}")
        
        data = self._make_request(endpoint, params)
        
        results = data.get('results', [])
        
        contracts = []
        for result in results:
            contract = OptionContract(
                ticker=result.get('ticker', ''),
                underlying_ticker=result.get('underlying_ticker', ''),
                contract_type=result.get('contract_type', ''),
                strike_price=result.get('strike_price', 0),
                expiration_date=result.get('expiration_date', ''),
                exercise_style=result.get('exercise_style', ''),
                shares_per_contract=result.get('shares_per_contract', 100)
            )
            contracts.append(contract)
        
        print(f"✅ Retrieved {len(contracts)} option contracts for {underlying_ticker}")
        return contracts
    
    def get_option_quotes(self, 
                         option_ticker: str,
                         timestamp: Optional[str] = None) -> Optional[OptionQuote]:
        """
        Get last quote for an option contract
        Ref: https://polygon.io/docs/options/get_v3_quotes__optionsticker
        """
        
        endpoint = f"/v3/quotes/{option_ticker}"
        params = {}
        
        if timestamp:
            params['timestamp'] = timestamp
        
        print(f"💰 Fetching option quote for {option_ticker}")
        
        data = self._make_request(endpoint, params)
        
        results = data.get('results', [])
        
        if not results:
            print(f"⚠️ No quote data for {option_ticker}")
            return None
        
        result = results[0]  # Get the latest quote
        
        quote = OptionQuote(
            ticker=option_ticker,
            bid=result.get('bid', 0),
            ask=result.get('ask', 0),
            bid_size=result.get('bid_size', 0),
            ask_size=result.get('ask_size', 0),
            last_quote_timestamp=result.get('last_quote_timestamp', 0)
        )
        
        return quote
    
    def get_option_trades(self, 
                         option_ticker: str,
                         timestamp_gte: Optional[str] = None,
                         timestamp_lt: Optional[str] = None,
                         limit: int = 1000) -> List[OptionTrade]:
        """
        Get trades for an option contract
        Ref: https://polygon.io/docs/options/get_v3_trades__optionsticker
        """
        
        endpoint = f"/v3/trades/{option_ticker}"
        params = {
            'limit': limit,
            'sort': 'timestamp'
        }
        
        if timestamp_gte:
            params['timestamp.gte'] = timestamp_gte
        if timestamp_lt:
            params['timestamp.lt'] = timestamp_lt
        
        print(f"📈 Fetching option trades for {option_ticker}")
        
        data = self._make_request(endpoint, params)
        
        results = data.get('results', [])
        
        trades = []
        for result in results:
            trade = OptionTrade(
                ticker=option_ticker,
                timestamp=result.get('participant_timestamp', 0),
                price=result.get('price', 0),
                size=result.get('size', 0),
                exchange=result.get('exchange', 0),
                sip_timestamp=result.get('sip_timestamp', 0)
            )
            trades.append(trade)
        
        print(f"✅ Retrieved {len(trades)} option trades for {option_ticker}")
        return trades
    
    def get_option_aggregates(self,
                            option_ticker: str,
                            multiplier: int = 1,
                            timespan: str = "day",
                            from_date: Union[str, datetime] = None,
                            to_date: Union[str, datetime] = None,
                            limit: int = 5000) -> List[Dict]:
        """
        Get aggregate bars for options
        Ref: https://polygon.io/docs/options/get_v2_aggs_ticker__optionsticker__range__multiplier___timespan___from___to
        """
        
        if from_date is None:
            from_date = datetime.now() - timedelta(days=7)
        if to_date is None:
            to_date = datetime.now()
        
        # Convert dates to strings if needed
        if isinstance(from_date, datetime):
            from_date = from_date.strftime('%Y-%m-%d')
        if isinstance(to_date, datetime):
            to_date = to_date.strftime('%Y-%m-%d')
        
        endpoint = f"/v2/aggs/ticker/{option_ticker}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
        params = {
            'adjusted': 'true',
            'sort': 'asc',
            'limit': limit
        }
        
        print(f"📊 Fetching option aggregates for {option_ticker}")
        
        data = self._make_request(endpoint, params)
        
        results = data.get('results', [])
        
        print(f"✅ Retrieved {len(results)} option aggregate bars")
        return results
    
    # ANALYSIS METHODS
    def analyze_unusual_volume(self, 
                             tickers: List[str], 
                             days_back: int = 30,
                             volume_threshold: float = 2.0) -> Dict[str, Dict]:
        """
        Analyze unusual volume patterns using Polygon.io data
        """
        print(f"🔍 Analyzing unusual volume for {len(tickers)} tickers...")
        
        analysis_results = {}
        
        for ticker in tickers:
            try:
                # Get historical stock data
                stock_bars = self.get_stock_aggregates(
                    ticker=ticker,
                    from_date=datetime.now() - timedelta(days=days_back),
                    to_date=datetime.now()
                )
                
                if len(stock_bars) < 10:  # Need minimum data for analysis
                    continue
                
                # Convert to DataFrame for analysis
                df = pd.DataFrame([{
                    'date': datetime.fromtimestamp(bar.timestamp / 1000).date(),
                    'volume': bar.volume,
                    'transactions': bar.transactions,
                    'close': bar.close,
                    'vwap': bar.vwap
                } for bar in stock_bars])
                
                # Calculate rolling averages
                df['volume_5d_avg'] = df['volume'].rolling(window=5).mean()
                df['volume_5d_std'] = df['volume'].rolling(window=5).std()
                df['transactions_5d_avg'] = df['transactions'].rolling(window=5).mean()
                df['transactions_5d_std'] = df['transactions'].rolling(window=5).std()
                
                # Get latest data point
                latest = df.iloc[-1]
                
                # Calculate z-scores
                volume_z_score = 0
                transactions_z_score = 0
                
                if latest['volume_5d_std'] > 0:
                    volume_z_score = (latest['volume'] - latest['volume_5d_avg']) / latest['volume_5d_std']
                
                if latest['transactions_5d_std'] > 0:
                    transactions_z_score = (latest['transactions'] - latest['transactions_5d_avg']) / latest['transactions_5d_std']
                
                # Check for unusual activity
                is_unusual = (volume_z_score >= volume_threshold or 
                            transactions_z_score >= volume_threshold)
                
                if is_unusual:
                    analysis_results[ticker] = {
                        'volume_z_score': volume_z_score,
                        'transactions_z_score': transactions_z_score,
                        'latest_volume': latest['volume'],
                        'avg_volume': latest['volume_5d_avg'],
                        'latest_transactions': latest['transactions'],
                        'avg_transactions': latest['transactions_5d_avg'],
                        'latest_close': latest['close'],
                        'volume_ratio': latest['volume'] / latest['volume_5d_avg'] if latest['volume_5d_avg'] > 0 else 0,
                        'is_unusual': True
                    }
                    
                    print(f"🔥 {ticker}: Volume Z-score {volume_z_score:.2f}, Transactions Z-score {transactions_z_score:.2f}")
                
            except Exception as e:
                print(f"❌ Error analyzing {ticker}: {e}")
                continue
        
        print(f"📊 Analysis complete: {len(analysis_results)} tickers with unusual activity")
        return analysis_results
    
    def get_high_volume_options(self, 
                              underlying_tickers: List[str],
                              min_volume_threshold: int = 1000) -> Dict[str, List[Dict]]:
        """
        Find high volume options for given underlying tickers
        """
        print(f"🎯 Finding high volume options for {len(underlying_tickers)} underlyings...")
        
        high_volume_options = {}
        
        for ticker in underlying_tickers:
            try:
                # Get option contracts
                contracts = self.get_option_contracts(
                    underlying_ticker=ticker,
                    limit=500  # Limit to avoid rate limits
                )
                
                if not contracts:
                    continue
                
                # Focus on near-term options (next 30 days)
                cutoff_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
                near_term_contracts = [
                    c for c in contracts 
                    if c.expiration_date <= cutoff_date
                ]
                
                # Sample a subset to avoid rate limits
                sample_contracts = near_term_contracts[:20]  # Limit to 20 for free tier
                
                ticker_options = []
                
                for contract in sample_contracts:
                    try:
                        # Get option aggregates to check volume
                        aggregates = self.get_option_aggregates(
                            option_ticker=contract.ticker,
                            from_date=datetime.now() - timedelta(days=1),
                            to_date=datetime.now()
                        )
                        
                        if aggregates:
                            latest_aggregate = aggregates[-1]
                            volume = latest_aggregate.get('v', 0)
                            
                            if volume >= min_volume_threshold:
                                ticker_options.append({
                                    'option_ticker': contract.ticker,
                                    'contract_type': contract.contract_type,
                                    'strike_price': contract.strike_price,
                                    'expiration_date': contract.expiration_date,
                                    'volume': volume,
                                    'close': latest_aggregate.get('c', 0),
                                    'transactions': latest_aggregate.get('n', 0)
                                })
                    
                    except Exception as e:
                        print(f"⚠️ Error processing option {contract.ticker}: {e}")
                        continue
                
                if ticker_options:
                    # Sort by volume descending
                    ticker_options.sort(key=lambda x: x['volume'], reverse=True)
                    high_volume_options[ticker] = ticker_options
                    
                    print(f"📈 {ticker}: Found {len(ticker_options)} high volume options")
                
            except Exception as e:
                print(f"❌ Error processing {ticker}: {e}")
                continue
        
        print(f"✅ High volume options analysis complete: {len(high_volume_options)} underlyings with activity")
        return high_volume_options
    
    def get_snapshot_all_tickers(self, ticker_types: str = "stocks") -> Dict:
        """
        Get snapshot of all tickers (useful for market overview)
        Ref: https://polygon.io/docs/stocks/get_v2_snapshot_locale_us_markets_stocks_tickers
        """
        endpoint = f"/v2/snapshot/locale/us/markets/{ticker_types}/tickers"
        
        print(f"📸 Getting market snapshot for {ticker_types}")
        
        try:
            data = self._make_request(endpoint)
            
            results = data.get('tickers', [])
            
            # Process and filter for most active
            active_tickers = []
            for ticker_data in results:
                ticker_info = ticker_data.get('ticker', '')
                day_data = ticker_data.get('day', {})
                prev_day_data = ticker_data.get('prevDay', {})
                
                if day_data.get('v', 0) > 1000000:  # Volume > 1M
                    active_tickers.append({
                        'ticker': ticker_info,
                        'volume': day_data.get('v', 0),
                        'close': day_data.get('c', 0),
                        'change_pct': ticker_data.get('todaysChangePerc', 0),
                        'transactions': day_data.get('n', 0)
                    })
            
            # Sort by volume
            active_tickers.sort(key=lambda x: x['volume'], reverse=True)
            
            print(f"✅ Market snapshot: {len(active_tickers)} active tickers")
            
            return {
                'timestamp': data.get('timestamp'),
                'active_tickers': active_tickers[:50]  # Top 50
            }
            
        except Exception as e:
            print(f"❌ Error getting market snapshot: {e}")
            return {'active_tickers': []}

# Factory function pour créer le client
def create_polygon_client(api_key: str) -> PolygonClient:
    """Factory function to create a Polygon client"""
    if not api_key or api_key == "YOUR_POLYGON_API_KEY_HERE":
        raise ValueError("Valid Polygon.io API key required")
    
    return PolygonClient(api_key)

# Test function
def test_polygon_client():
    """Test the Polygon.io client with mock API key"""
    print("🧪 Testing Polygon.io Client (requires valid API key)")
    
    # This would need a real API key to work
    api_key = "test_key"  # Replace with real key
    
    try:
        client = create_polygon_client(api_key)
        
        # Test market status
        status = client.get_market_status()
        print(f"Market status: {status}")
        
        # Test stock aggregates
        bars = client.get_stock_aggregates('SPY', from_date=datetime.now() - timedelta(days=5))
        print(f"SPY bars retrieved: {len(bars)}")
        
        print("✅ Polygon.io client test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_polygon_client()