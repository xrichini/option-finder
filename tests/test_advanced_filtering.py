#!/usr/bin/env python3
"""
Tests for Advanced Filtering and WebSocket Features
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from typing import List, Dict, Any

from app import app
from services.advanced_filtering_service import advanced_filtering_service
from models.api_models import AdvancedFilters, FilterPreset

client = TestClient(app)


class TestAdvancedFilteringService:
    """Tests for AdvancedFilteringService"""

    @pytest.fixture
    def sample_opportunities(self) -> List[Dict[str, Any]]:
        """Sample options data for testing"""
        return [
            {
                "symbol": "AAPL",
                "strike": 150,
                "dte": 7,
                "last_price": 2.5,
                "volume_1d": 100,
                "open_interest": 500,
                "implied_volatility": 30,
                "whale_score": 75,
                "delta": 0.5,
            },
            {
                "symbol": "AAPL",
                "strike": 155,
                "dte": 14,
                "last_price": 1.5,
                "volume_1d": 50,
                "open_interest": 200,
                "implied_volatility": 28,
                "whale_score": 45,
                "delta": 0.3,
            },
            {
                "symbol": "TSLA",
                "strike": 200,
                "dte": 21,
                "last_price": 4.0,
                "volume_1d": 150,
                "open_interest": 800,
                "implied_volatility": 45,
                "whale_score": 65,
                "delta": 0.6,
            },
        ]

    def test_filter_by_whale_score(self, sample_opportunities):
        """Test filtering by whale score"""
        filters = AdvancedFilters(min_whale_score=50.0)
        result = advanced_filtering_service.filter_opportunities(
            sample_opportunities, filters
        )
        assert len(result) == 2
        assert all(opp["whale_score"] >= 50 for opp in result)

    def test_filter_by_price_range(self, sample_opportunities):
        """Test filtering by price range"""
        filters = AdvancedFilters(min_price=1.5, max_price=3.0)
        result = advanced_filtering_service.filter_opportunities(
            sample_opportunities, filters
        )
        assert len(result) == 2
        assert all(1.5 <= opp["last_price"] <= 3.0 for opp in result)

    def test_filter_by_dte(self, sample_opportunities):
        """Test filtering by DTE"""
        filters = AdvancedFilters(min_dte=7, max_dte=14)
        result = advanced_filtering_service.filter_opportunities(
            sample_opportunities, filters
        )
        assert len(result) == 2
        assert all(7 <= opp["dte"] <= 14 for opp in result)

    def test_filter_multiple_criteria(self, sample_opportunities):
        """Test filtering by multiple criteria"""
        filters = AdvancedFilters(
            min_whale_score=50.0,
            min_dte=7,
            max_price=2.5,
            min_volume=100,
        )
        result = advanced_filtering_service.filter_opportunities(
            sample_opportunities, filters
        )
        assert len(result) == 1
        assert result[0]["symbol"] == "AAPL"
        assert result[0]["strike"] == 150

    def test_apply_preset_aggressive(self, sample_opportunities):
        """Test applying aggressive preset"""
        result = advanced_filtering_service.apply_preset(
            sample_opportunities, "aggressive"
        )
        assert len(result) > 0
        assert all(opp["whale_score"] >= 70 for opp in result)

    def test_apply_preset_balanced(self, sample_opportunities):
        """Test applying balanced preset (default)"""
        result = advanced_filtering_service.apply_preset(
            sample_opportunities, "balanced"
        )
        assert len(result) > 0
        assert all(opp["whale_score"] >= 50 for opp in result)

    def test_sort_by_whale_score(self, sample_opportunities):
        """Test sorting by whale score"""
        result = advanced_filtering_service.sort_opportunities(
            sample_opportunities, sort_by="whale_score", ascending=False
        )
        scores = [opp["whale_score"] for opp in result]
        assert scores == sorted(scores, reverse=True)

    def test_sort_by_volume(self, sample_opportunities):
        """Test sorting by volume"""
        result = advanced_filtering_service.sort_opportunities(
            sample_opportunities, sort_by="volume", ascending=True
        )
        volumes = [opp["volume_1d"] for opp in result]
        assert volumes == sorted(volumes)

    def test_sort_by_price(self, sample_opportunities):
        """Test sorting by price"""
        result = advanced_filtering_service.sort_opportunities(
            sample_opportunities, sort_by="price", ascending=False
        )
        prices = [opp["last_price"] for opp in result]
        assert prices == sorted(prices, reverse=True)

    def test_get_all_presets(self):
        """Test retrieving all presets"""
        presets = advanced_filtering_service.get_all_presets()
        assert len(presets) >= 6
        assert "balanced" in presets
        assert "aggressive" in presets
        assert "conservative" in presets

    def test_get_preset(self):
        """Test retrieving specific preset"""
        preset = advanced_filtering_service.get_preset("aggressive")
        assert preset is not None
        assert preset.name == "Aggressive"

    def test_create_custom_preset(self):
        """Test creating custom preset"""
        filters = AdvancedFilters(min_whale_score=80, max_price=1.0)
        preset = advanced_filtering_service.create_custom_preset(
            "test_custom", filters, "Test custom preset"
        )
        assert preset.name == "test_custom"
        assert preset.filters.min_whale_score == 80

    def test_delete_preset(self):
        """Test deleting custom preset"""
        # First create one
        filters = AdvancedFilters(min_whale_score=80)
        advanced_filtering_service.create_custom_preset("deleteme", filters)

        # Then delete it
        success = advanced_filtering_service.delete_preset("deleteme")
        assert success is True

    def test_get_filter_stats(self, sample_opportunities):
        """Test getting statistics"""
        stats = advanced_filtering_service.get_filter_stats(sample_opportunities)
        assert stats["total"] == 3
        assert stats["avg_whale_score"] > 0
        assert len(stats["price_range"]) == 2
        assert len(stats["dte_range"]) == 2

    def test_get_filter_stats_empty(self):
        """Test getting statistics for empty list"""
        stats = advanced_filtering_service.get_filter_stats([])
        assert stats["total"] == 0
        assert stats["avg_whale_score"] == 0

    def test_export_filters_json(self):
        """Test exporting filters as JSON"""
        filters = AdvancedFilters(min_whale_score=50, max_price=5.0, min_volume=100)
        json_str = advanced_filtering_service.export_filters_json(filters)
        assert isinstance(json_str, str)
        assert "min_whale_score" in json_str
        assert "50" in json_str

    def test_import_filters_json(self):
        """Test importing filters from JSON"""
        json_str = '{"min_whale_score": 60, "max_price": 3.0}'
        filters = advanced_filtering_service.import_filters_json(json_str)
        assert filters is not None
        assert filters.min_whale_score == 60
        assert filters.max_price == 3.0


class TestFilteringAPI:
    """Tests for Filtering API Endpoints"""

    def test_get_presets_endpoint(self):
        """Test GET /api/filtering/presets"""
        response = client.get("/api/filtering/presets")
        assert response.status_code == 200
        presets = response.json()
        assert len(presets) >= 6

    def test_get_preset_details_endpoint(self):
        """Test GET /api/filtering/presets/{preset_name}"""
        response = client.get("/api/filtering/presets/aggressive")
        assert response.status_code == 200
        preset = response.json()
        assert preset["name"] == "Aggressive"

    def test_apply_filters_endpoint(self):
        """Test POST /api/filtering/apply"""
        opportunities = [
            {
                "symbol": "TEST",
                "whale_score": 75,
                "last_price": 2.0,
                "volume_1d": 100,
            }
        ]
        filters = {
            "min_whale_score": 50,
            "max_price": 5.0,
        }
        response = client.post(
            "/api/filtering/apply",
            json={"opportunities": opportunities, "filters": filters},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["original_count"] == 1
        assert result["filtered_count"] == 1

    def test_sort_endpoint(self):
        """Test POST /api/filtering/sort"""
        opportunities = [
            {"whale_score": 50, "symbol": "A"},
            {"whale_score": 80, "symbol": "B"},
            {"whale_score": 60, "symbol": "C"},
        ]
        response = client.post(
            "/api/filtering/sort?sort_by=whale_score&ascending=false",
            json=opportunities,
        )
        assert response.status_code == 200
        result = response.json()
        assert result["count"] == 3


class TestWebSocketFeature:
    """Tests for WebSocket functionality"""

    def test_websocket_connection(self):
        """Test WebSocket connection"""
        with client.websocket_connect("/ws") as websocket:
            # Server should accept connection
            assert websocket.application_state.name == "connected"

    def test_websocket_receive_message(self):
        """Test receiving WebSocket message"""
        with client.websocket_connect("/ws") as websocket:
            # Send a message (if supported)
            # Check that connection is active
            assert websocket.application_state.name == "connected"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
