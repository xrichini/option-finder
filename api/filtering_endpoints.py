#!/usr/bin/env python3
"""
Advanced Filtering Endpoints - REST API for advanced filtering
"""

from fastapi import APIRouter, Query
from typing import List, Optional, Dict, Any
import logging

from models.api_models import (
    AdvancedFilters,
    AdvancedScreeningRequest,
    FilterPreset,
    OptionsOpportunity,
)
from services.advanced_filtering_service import advanced_filtering_service
from services.hybrid_screening_service import hybrid_screening_service

logger = logging.getLogger(__name__)

filtering_router = APIRouter(prefix="/api/filtering", tags=["Filtering"])


@filtering_router.get("/presets")
async def get_filter_presets() -> Dict[str, FilterPreset]:
    """Get all available filter presets"""
    return {name: preset for name, preset in advanced_filtering_service.get_all_presets().items()}


@filtering_router.get("/presets/{preset_name}")
async def get_preset_details(preset_name: str) -> Optional[FilterPreset]:
    """Get specific preset details"""
    preset = advanced_filtering_service.get_preset(preset_name)
    if not preset:
        return {"error": f"Preset '{preset_name}' not found"}
    return preset


@filtering_router.post("/apply")
async def apply_filters(
    opportunities: List[Dict[str, Any]],
    filters: AdvancedFilters,
) -> List[Dict[str, Any]]:
    """
    Apply advanced filters to opportunities list
    Returns filtered opportunities
    """
    filtered = advanced_filtering_service.filter_opportunities(opportunities, filters)
    return {
        "original_count": len(opportunities),
        "filtered_count": len(filtered),
        "opportunities": filtered,
    }


@filtering_router.post("/apply-preset")
async def apply_preset_filter(
    opportunities: List[Dict[str, Any]],
    preset_name: str = Query(..., description="Name of the preset to apply"),
) -> Dict[str, Any]:
    """Apply a named preset to opportunities"""
    filtered = advanced_filtering_service.apply_preset(opportunities, preset_name)
    return {
        "preset_name": preset_name,
        "original_count": len(opportunities),
        "filtered_count": len(filtered),
        "opportunities": filtered,
    }


@filtering_router.post("/sort")
async def sort_opportunities(
    opportunities: List[Dict[str, Any]],
    sort_by: str = Query("whale_score", description="Field to sort by"),
    ascending: bool = Query(False, description="Sort ascending?"),
) -> Dict[str, Any]:
    """
    Sort opportunities by various criteria
    
    Supported fields: whale_score, volume, price, dte, delta, iv, oi, strike
    """
    sorted_opps = advanced_filtering_service.sort_opportunities(
        opportunities, sort_by=sort_by, ascending=ascending
    )
    return {
        "sort_field": sort_by,
        "ascending": ascending,
        "count": len(sorted_opps),
        "opportunities": sorted_opps,
    }


@filtering_router.post("/filter-and-sort")
async def filter_and_sort(
    opportunities: List[Dict[str, Any]],
    filters: Optional[AdvancedFilters] = None,
    preset_name: Optional[str] = None,
    sort_by: str = Query("whale_score"),
    ascending: bool = Query(False),
) -> Dict[str, Any]:
    """Apply filters and sort in one operation"""
    
    # Apply filters (either preset or custom)
    if preset_name:
        filtered = advanced_filtering_service.apply_preset(opportunities, preset_name)
    elif filters:
        filtered = advanced_filtering_service.filter_opportunities(opportunities, filters)
    else:
        filtered = opportunities

    # Sort results
    sorted_opps = advanced_filtering_service.sort_opportunities(
        filtered, sort_by=sort_by, ascending=ascending
    )

    return {
        "original_count": len(opportunities),
        "filtered_count": len(filtered),
        "final_count": len(sorted_opps),
        "sort_field": sort_by,
        "sort_ascending": ascending,
        "opportunities": sorted_opps,
    }


@filtering_router.get("/stats")
async def get_filter_stats(opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Get statistics about opportunities for UI"""
    stats = advanced_filtering_service.get_filter_stats(opportunities)
    return {
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        "stats": stats,
    }


@filtering_router.post("/custom-preset")
async def create_custom_preset(
    name: str = Query(..., description="Preset name"),
    description: str = Query("", description="Preset description"),
    filters: AdvancedFilters = None,
) -> FilterPreset:
    """Create a custom filter preset"""
    preset = advanced_filtering_service.create_custom_preset(
        name=name, filters=filters or AdvancedFilters(), description=description
    )
    return preset


@filtering_router.delete("/custom-preset/{preset_name}")
async def delete_custom_preset(preset_name: str) -> Dict[str, Any]:
    """Delete a custom preset"""
    success = advanced_filtering_service.delete_preset(preset_name)
    return {
        "preset_name": preset_name,
        "deleted": success,
        "message": f"Preset '{preset_name}' deleted successfully"
        if success
        else f"Could not delete preset '{preset_name}' (may be default or non-existent)",
    }


@filtering_router.get("/export")
async def export_filters(
    filters: AdvancedFilters,
) -> Dict[str, str]:
    """Export filters as JSON"""
    json_str = advanced_filtering_service.export_filters_json(filters)
    return {
        "json": json_str,
        "filters": filters.dict(exclude_none=True),
    }
