#!/usr/bin/env python3
"""
Advanced Filtering Service - Apply complex filters to option opportunities
Supports multiple filter combinations and preset management
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from models.api_models import (
    AdvancedFilters,
    FilterPreset,
    OptionsOpportunity,
)

logger = logging.getLogger(__name__)


class AdvancedFilteringService:
    """Service for advanced option filtering with presets"""

    def __init__(self):
        self.presets: Dict[str, FilterPreset] = {}
        self._load_default_presets()

    def _load_default_presets(self):
        """Load built-in filter presets"""
        # Preset: Aggressive (high whale score, low price)
        self.presets["aggressive"] = FilterPreset(
            name="Aggressive",
            description="High whale activity, cheap options",
            filters=AdvancedFilters(
                min_whale_score=70.0,
                max_price=2.0,
                min_volume=100,
                min_dte=1,
                max_dte=45,
            ),
            is_default=False,
        )

        # Preset: Conservative (moderate filters)
        self.presets["conservative"] = FilterPreset(
            name="Conservative",
            description="Moderate risk, established options",
            filters=AdvancedFilters(
                min_whale_score=40.0,
                max_price=10.0,
                min_volume=50,
                min_dte=3,
                max_dte=60,
                min_oi=100,
            ),
            is_default=False,
        )

        # Preset: Balanced (default)
        self.presets["balanced"] = FilterPreset(
            name="Balanced",
            description="Balanced risk-reward (default)",
            filters=AdvancedFilters(
                min_whale_score=50.0,
                max_price=5.0,
                min_volume=75,
                min_dte=1,
                max_dte=45,
                min_oi=50,
            ),
            is_default=True,
        )

        # Preset: High IV (volatility plays)
        self.presets["high_iv"] = FilterPreset(
            name="High IV",
            description="Elevated implied volatility plays",
            filters=AdvancedFilters(
                min_iv=50.0,
                min_whale_score=30.0,
                min_volume=50,
                min_dte=7,
            ),
            is_default=False,
        )

        # Preset: Near-term (0-7 DTE)
        self.presets["near_term"] = FilterPreset(
            name="Near-Term",
            description="Expiring this week (0-7 DTE)",
            filters=AdvancedFilters(
                min_dte=0,
                max_dte=7,
                min_whale_score=40.0,
                min_volume=100,
            ),
            is_default=False,
        )

        # Preset: Medium-term (7-30 DTE)
        self.presets["medium_term"] = FilterPreset(
            name="Medium-Term",
            description="Mid-range expiration (7-30 DTE)",
            filters=AdvancedFilters(
                min_dte=7,
                max_dte=30,
                min_whale_score=50.0,
                min_volume=75,
            ),
            is_default=False,
        )

    def filter_opportunities(
        self, opportunities: List[Dict[str, Any]], filters: AdvancedFilters
    ) -> List[Dict[str, Any]]:
        """Apply advanced filters to opportunities list"""

        if not filters or not any(
            getattr(filters, field) is not None for field in filters.model_fields
        ):
            # No filters applied
            return opportunities

        filtered = opportunities

        # Strike filters
        if filters.min_strike is not None:
            filtered = [
                opp
                for opp in filtered
                if opp.get("strike", float("inf")) >= filters.min_strike
            ]

        if filters.max_strike is not None:
            filtered = [
                opp for opp in filtered if opp.get("strike", 0) <= filters.max_strike
            ]

        # DTE filters
        if filters.min_dte is not None:
            filtered = [opp for opp in filtered if opp.get("dte", 0) >= filters.min_dte]

        if filters.max_dte is not None:
            filtered = [
                opp for opp in filtered if opp.get("dte", 999) <= filters.max_dte
            ]

        # IV filters
        if filters.min_iv is not None:
            filtered = [
                opp
                for opp in filtered
                if opp.get("implied_volatility", 0) >= filters.min_iv
            ]

        if filters.max_iv is not None:
            filtered = [
                opp
                for opp in filtered
                if opp.get("implied_volatility", 999) <= filters.max_iv
            ]

        # Volume filters
        if filters.min_volume is not None:
            filtered = [
                opp for opp in filtered if opp.get("volume_1d", 0) >= filters.min_volume
            ]

        if filters.max_volume is not None:
            filtered = [
                opp
                for opp in filtered
                if opp.get("volume_1d", 999999) <= filters.max_volume
            ]

        # Open Interest filters
        if filters.min_oi is not None:
            filtered = [
                opp for opp in filtered if opp.get("open_interest", 0) >= filters.min_oi
            ]

        if filters.max_oi is not None:
            filtered = [
                opp
                for opp in filtered
                if opp.get("open_interest", 999999) <= filters.max_oi
            ]

        # Delta filters
        if filters.min_delta is not None:
            filtered = [
                opp for opp in filtered if opp.get("delta", -1) >= filters.min_delta
            ]

        if filters.max_delta is not None:
            filtered = [
                opp for opp in filtered if opp.get("delta", 2) <= filters.max_delta
            ]

        # Whale score filters
        if filters.min_whale_score is not None:
            filtered = [
                opp
                for opp in filtered
                if opp.get("whale_score", 0) >= filters.min_whale_score
            ]

        if filters.max_whale_score is not None:
            filtered = [
                opp
                for opp in filtered
                if opp.get("whale_score", 100) <= filters.max_whale_score
            ]

        # Price filters
        if filters.min_price is not None:
            filtered = [
                opp for opp in filtered if opp.get("last_price", 0) >= filters.min_price
            ]

        if filters.max_price is not None:
            filtered = [
                opp
                for opp in filtered
                if opp.get("last_price", 999999) <= filters.max_price
            ]

        logger.info(
            f"Applied filters: {opportunities.__len__()} → {filtered.__len__()} opportunities"
        )
        return filtered

    def apply_preset(
        self, opportunities: List[Dict[str, Any]], preset_name: str
    ) -> List[Dict[str, Any]]:
        """Apply a named preset to opportunities"""
        if preset_name not in self.presets:
            logger.warning(
                f"Preset '{preset_name}' not found, returning all opportunities"
            )
            return opportunities

        preset = self.presets[preset_name]
        return self.filter_opportunities(opportunities, preset.filters)

    def get_preset(self, preset_name: str) -> Optional[FilterPreset]:
        """Get a preset by name"""
        return self.presets.get(preset_name)

    def get_all_presets(self) -> Dict[str, FilterPreset]:
        """Get all available presets"""
        return self.presets

    def create_custom_preset(
        self, name: str, filters: AdvancedFilters, description: str = ""
    ) -> FilterPreset:
        """Create and register a custom preset"""
        preset = FilterPreset(name=name, description=description, filters=filters)
        self.presets[name.lower().replace(" ", "_")] = preset
        logger.info(f"Custom preset created: {name}")
        return preset

    def delete_preset(self, preset_name: str) -> bool:
        """Delete a custom preset (not default ones)"""
        if preset_name not in self.presets:
            return False

        preset = self.presets[preset_name]
        if preset.is_default:
            logger.warning(f"Cannot delete default preset: {preset_name}")
            return False

        del self.presets[preset_name]
        logger.info(f"Preset deleted: {preset_name}")
        return True

    def sort_opportunities(
        self,
        opportunities: List[Dict[str, Any]],
        sort_by: str = "whale_score",
        ascending: bool = False,
    ) -> List[Dict[str, Any]]:
        """Sort opportunities by various criteria"""
        sort_fields = {
            "whale_score": "whale_score",
            "volume": "volume_1d",
            "price": "last_price",
            "dte": "dte",
            "delta": "delta",
            "iv": "implied_volatility",
            "oi": "open_interest",
            "strike": "strike",
        }

        field = sort_fields.get(sort_by, "whale_score")
        try:
            sorted_opps = sorted(
                opportunities,
                key=lambda x: x.get(field, 0) if x.get(field) is not None else 0,
                reverse=not ascending,
            )
            logger.info(f"Sorted {len(sorted_opps)} opportunities by {sort_by}")
            return sorted_opps
        except Exception as e:
            logger.error(f"Error sorting opportunities: {e}")
            return opportunities

    def export_filters_json(self, filters: AdvancedFilters) -> str:
        """Export filters as JSON string"""
        return filters.model_dump_json(exclude_none=True)

    def import_filters_json(self, json_str: str) -> Optional[AdvancedFilters]:
        """Import filters from JSON string"""
        try:
            data = json.loads(json_str)
            return AdvancedFilters(**data)
        except Exception as e:
            logger.error(f"Error importing filters: {e}")
            return None

    def get_filter_stats(self, opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about opportunities for UI display"""
        if not opportunities:
            return {
                "total": 0,
                "avg_whale_score": 0,
                "price_range": [0, 0],
                "dte_range": [0, 0],
                "volume_range": [0, 0],
            }

        whale_scores = [opp.get("whale_score", 0) for opp in opportunities]
        prices = [opp.get("last_price", 0) for opp in opportunities]
        dtes = [opp.get("dte", 0) for opp in opportunities]
        volumes = [opp.get("volume_1d", 0) for opp in opportunities]

        return {
            "total": len(opportunities),
            "avg_whale_score": (
                sum(whale_scores) / len(whale_scores) if whale_scores else 0
            ),
            "price_range": [min(prices) if prices else 0, max(prices) if prices else 0],
            "dte_range": [min(dtes) if dtes else 0, max(dtes) if dtes else 0],
            "volume_range": [
                min(volumes) if volumes else 0,
                max(volumes) if volumes else 0,
            ],
        }


# Global instance
advanced_filtering_service = AdvancedFilteringService()
