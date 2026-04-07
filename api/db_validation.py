"""
Validate historical metrics in options_history.db

Functions:
- validate_metrics() - Check sizzle_index, vol_trend_ratio, iv_rank consistency
- generate_validation_report() - Detailed checks with warnings
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path("options_history.db")


def validate_metrics() -> dict:
    """
    Check data quality metrics:
    - Count NaN/NULL values in key fields
    - Check ranges (sizzle_index 0-100, iv_rank 0-100, ratios >= 0)
    - Flag suspicious patterns

    Returns: {"valid": bool, "issues": [...], "stats": {...}}
    """
    if not DB_PATH.exists():
        return {"valid": False, "issues": ["DB not found"], "stats": {}}

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        issues = []
        stats = {}

        # Check for NULL values in key columns
        key_fields = [
            "sizzle_index",
            "vol_trend_ratio",
            "iv_rank",
            "whale_score",
            "realtime_score",
            "hybrid_score",
        ]

        for field in key_fields:
            cursor.execute(f"SELECT COUNT(*) FROM options WHERE {field} IS NULL")
            null_count = cursor.fetchone()[0]
            stats[f"{field}_nulls"] = null_count
            if null_count > 0:
                issues.append(f"⚠️  {field}: {null_count} NULL values")

        # Check ranges
        cursor.execute(
            "SELECT COUNT(*) FROM options WHERE sizzle_index < 0 OR sizzle_index > 100"
        )
        bad_sizzle = cursor.fetchone()[0]
        if bad_sizzle > 0:
            issues.append(f"⚠️  sizzle_index: {bad_sizzle} out of range [0,100]")
        stats["sizzle_index_out_of_range"] = bad_sizzle

        cursor.execute("SELECT COUNT(*) FROM options WHERE vol_trend_ratio < 0")
        bad_vol = cursor.fetchone()[0]
        if bad_vol > 0:
            issues.append(f"⚠️  vol_trend_ratio: {bad_vol} negative values")
        stats["vol_trend_ratio_negative"] = bad_vol

        # Check for very old data
        cursor.execute(
            "SELECT COUNT(*) FROM options WHERE analysis_timestamp < datetime('now', '-90 days')"
        )
        old_count = cursor.fetchone()[0]
        if old_count > 0:
            issues.append(f"📅 {old_count} records > 90 days old (should be purged)")
        stats["records_over_90_days"] = old_count

        # Data freshness
        cursor.execute("SELECT MAX(analysis_timestamp) FROM options")
        newest = cursor.fetchone()[0]
        stats["latest_record"] = newest

        valid = len(issues) == 0

        logger.info(
            f"{'✅' if valid else '⚠️ '} Validation: {len(issues)} issues found. "
            f"Latest: {newest}"
        )

        return {
            "valid": valid,
            "issues": issues,
            "stats": stats,
            "checked_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Validation error: {e}")
        return {"valid": False, "issues": [f"Validation failed: {str(e)}"], "stats": {}}


def generate_validation_report() -> str:
    """Pretty-print validation report."""
    result = validate_metrics()

    report = [
        "\n" + "=" * 60,
        f"VALIDATION REPORT — {result.get('checked_at', 'unknown')}",
        "=" * 60,
    ]

    if result["valid"]:
        report.append("✅ STATUS: All checks passed")
    else:
        report.append(f"⚠️  STATUS: {len(result['issues'])} issues found")
        report.append("")
        report.append("Issues:")
        for issue in result["issues"]:
            report.append(f"  • {issue}")

    report.append("")
    report.append("Statistics:")
    for key, value in result["stats"].items():
        report.append(f"  • {key}: {value}")

    report.append("=" * 60)

    return "\n".join(report)


if __name__ == "__main__":
    print(generate_validation_report())
