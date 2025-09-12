# tests/test_async_performance.py
import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from data.async_tradier import AsyncTradierClient, CacheEntry
from data.screener_logic import OptionsScreener
from utils.helpers import get_market_data_batch, filter_symbols_by_market_criteria


class TestAsyncTradierClient:
    
    @pytest.fixture
    def client(self):
        """Client for testing"""
        return AsyncTradierClient(max_concurrent=5, rate_limit=0.01)
    
    def test_cache_entry_expiration(self):
        """Test cache entry expiration logic"""
        # Fresh entry
        entry = CacheEntry(data="test", timestamp=time.time(), ttl=1)
        assert not entry.is_expired()
        
        # Expired entry
        old_entry = CacheEntry(data="test", timestamp=time.time() - 2, ttl=1)
        assert old_entry.is_expired()
    
    def test_get_cached_or_store(self, client):
        """Test caching mechanism"""
        # Store new data
        result = client._get_cached_or_store("test_key", "test_value")
        assert result == "test_value"
        assert "test_key" in client._cache
        
        # Retrieve cached data
        cached_result = client._get_cached_or_store("test_key", None)
        assert cached_result == "test_value"
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, client):
        """Test that rate limiting works"""
        start_time = time.time()
        
        # Mock the session and response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"test": "data"})
        
        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        
        client._session = mock_session
        
        # Make multiple requests
        tasks = [
            client._rate_limited_request('GET', 'http://test.com')
            for _ in range(3)
        ]
        
        await asyncio.gather(*tasks)
        
        elapsed = time.time() - start_time
        # Should take at least 2 * rate_limit seconds for 3 requests
        expected_min_time = 2 * client._rate_limit
        assert elapsed >= expected_min_time * 0.8  # Allow some tolerance
        
        await client.close()


class TestScreenerLogic:
    
    @pytest.fixture
    def screener(self):
        """Screener for testing"""
        return OptionsScreener(use_async=True)
    
    def test_whale_score_calculation(self, screener):
        """Test whale score calculation with various inputs"""
        # High volume, high score
        score = screener.calculate_whale_score(
            volume_1d=6000,
            volume_7d=25000,
            open_interest=1000,
            delta=0.5,
            iv=0.9
        )
        assert score >= 80  # Should be high score
        
        # Low volume, low score
        score = screener.calculate_whale_score(
            volume_1d=100,
            volume_7d=500,
            open_interest=1000,
            delta=0.1,
            iv=0.2
        )
        assert score <= 30  # Should be low score
    
    def test_process_option_with_valid_data(self, screener):
        """Test option processing with valid data"""
        mock_option = {
            "volume": 2000,
            "open_interest": 500,
            "symbol": "TEST240315C00100000",
            "expiration_date": "2024-03-15",
            "strike": 100.0,
            "last": 5.25,
            "bid": 5.00,
            "ask": 5.50,
            "greeks": {
                "delta": 0.65,
                "mid_iv": 0.45
            }
        }
        
        result = screener._process_option(
            mock_option, "TEST", "call", min_whale_score=50
        )
        
        assert result is not None
        assert result.symbol == "TEST"
        assert result.strike == 100.0
        assert result.volume_1d == 2000
    
    def test_process_option_with_missing_greeks(self, screener):
        """Test option processing with missing Greeks data"""
        mock_option = {
            "volume": 2000,
            "open_interest": 500,
            "symbol": "TEST240315C00100000",
            "expiration_date": "2024-03-15",
            "strike": 100.0,
            "last": 5.25,
            "bid": 5.00,
            "ask": 5.50,
            # No greeks data
        }
        
        result = screener._process_option(
            mock_option, "TEST", "call", min_whale_score=50
        )
        
        # Should still work with default values
        if result:
            assert result.delta == 0.3  # Default value
            assert result.implied_volatility == 0.4  # Default value


class TestHelpers:
    
    @patch('yfinance.Tickers')
    def test_market_data_batch(self, mock_tickers):
        """Test market data batch processing"""
        # Mock yfinance response
        mock_ticker = Mock()
        mock_ticker.info = {
            'marketCap': 200_000_000,
            'averageVolume': 1_000_000,
            'currentPrice': 50.0,
            'sector': 'Technology'
        }
        mock_ticker.history.return_value = Mock()
        mock_ticker.history.return_value.empty = False
        mock_ticker.history.return_value.__len__ = Mock(return_value=5)
        mock_ticker.history.return_value.__getitem__ = Mock(return_value=Mock(iloc=Mock(__getitem__=Mock(return_value=50.0)), mean=Mock(return_value=500_000)))
        
        mock_tickers_instance = Mock()
        mock_tickers_instance.tickers = {'AAPL': mock_ticker}
        mock_tickers.return_value = mock_tickers_instance
        
        # Test the function
        result = get_market_data_batch(['AAPL'])
        
        assert 'AAPL' in result
        assert result['AAPL']['market_cap'] == 200_000_000
        assert result['AAPL']['sector'] == 'Technology'
    
    def test_filter_symbols_by_market_criteria(self):
        """Test market criteria filtering"""
        # Mock market data
        symbols = ['AAPL', 'SMALL']
        
        with patch('utils.helpers.get_market_data_batch') as mock_get_data:
            mock_get_data.return_value = {
                'AAPL': {
                    'market_cap': 200_000_000,
                    'avg_volume': 1_000_000,
                    'sector': 'Technology'
                },
                'SMALL': {
                    'market_cap': 50_000_000,  # Below threshold
                    'avg_volume': 100_000,     # Below threshold
                    'sector': 'Technology'
                }
            }
            
            filtered = filter_symbols_by_market_criteria(
                symbols,
                min_market_cap=100_000_000,
                min_avg_volume=500_000
            )
            
            assert 'AAPL' in filtered
            assert 'SMALL' not in filtered


class TestPerformanceIntegration:
    
    @pytest.mark.asyncio
    async def test_batch_processing_performance(self):
        """Test that batch processing is faster than sequential"""
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        
        client = AsyncTradierClient(max_concurrent=3, rate_limit=0.01)
        
        # Mock the async method to avoid actual API calls
        async def mock_async_is_optionable(symbol):
            await asyncio.sleep(0.01)  # Simulate API delay
            return symbol in ['AAPL', 'MSFT', 'GOOGL']  # Mock some as optionable
        
        client.async_is_optionable = mock_async_is_optionable
        
        try:
            start_time = time.time()
            result = await client.filter_optionable_symbols(symbols)
            batch_time = time.time() - start_time
            
            # Should complete in less time than sequential
            max_expected_time = len(symbols) * 0.01  # If sequential
            assert batch_time < max_expected_time
            assert len(result) == 3  # AAPL, MSFT, GOOGL
            
        finally:
            await client.close()
    
    def test_progress_callback_functionality(self):
        """Test that progress callbacks work correctly"""
        screener = OptionsScreener(use_async=False)
        
        progress_calls = []
        
        def progress_callback(idx, symbol, options_found, details):
            progress_calls.append({
                'idx': idx,
                'symbol': symbol,
                'options_found': options_found,
                'details': details
            })
        
        # Mock the client methods to avoid API calls
        screener.client.get_option_expirations = Mock(return_value=[])
        
        # Test with single symbol
        screener._run_enhanced_screening(
            option_type="call",
            symbols=['TEST'],
            progress_callback=progress_callback
        )
        
        # Should have received progress callbacks
        assert len(progress_calls) > 0
        assert progress_calls[0]['symbol'] == 'TEST'


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_async_performance.py -v
    pytest.main([__file__, "-v"])