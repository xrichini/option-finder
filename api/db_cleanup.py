"""
Database cleanup utilities for options_history.db

Functions:
- purge_expired_options(conn, days_old=30) - Remove options expired > N days ago
- get_db_stats() - Size, record count, last purge date
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path("options_history.db")


def purge_expired_options(conn: sqlite3.Connection = None, days_old: int = 30) -> dict:
    """
    Remove options that expired more than days_old days ago.

    Returns: {"deleted": count, "remaining": count, "freed_mb": approx}
    """
    if conn is None:
        if not DB_PATH.exists():
            logger.warning(f"⚠️  {DB_PATH} not found, skipping purge")
            return {"deleted": 0, "remaining": 0, "freed_mb": 0.0}
        conn = sqlite3.connect(DB_PATH)

    try:
        cursor = conn.cursor()

        # Find cutoff date
        cutoff = (datetime.now() - timedelta(days=days_old)).date()

        # Count before
        cursor.execute(
            "SELECT COUNT(*) FROM options WHERE expiration_date < ?", (cutoff,)
        )
        delete_count = cursor.fetchone()[0]

        if delete_count == 0:
            logger.info(f"✅ No expired options to purge (cutoff: {cutoff})")
            return {"deleted": 0, "remaining": 0, "freed_mb": 0.0}

        # Delete
        cursor.execute("DELETE FROM options WHERE expiration_date < ?", (cutoff,))
        deleted = cursor.rowcount

        # Vacuum to reclaim space
        cursor.execute("VACUUM")
        conn.commit()

        # Count after
        cursor.execute("SELECT COUNT(*) FROM options")
        remaining = cursor.fetchone()[0]

        # Estimate freed space
        freed_mb = (
            (deleted / max(deleted + remaining, 1))
            * DB_PATH.stat().st_size
            / (1024 * 1024)
        )

        logger.info(
            f"🗑️  Purged {deleted} expired options (cutoff: {cutoff}). "
            f"Remaining: {remaining}, Freed: ~{freed_mb:.1f}MB"
        )
        return {
            "deleted": deleted,
            "remaining": remaining,
            "freed_mb": round(freed_mb, 2),
        }

    except sqlite3.Error as e:
        logger.error(f"❌ Purge failed: {e}")
        return {"deleted": 0, "remaining": 0, "freed_mb": 0.0}


def get_db_stats() -> dict:
    """Return DB file size, record count, schema info."""
    if not DB_PATH.exists():
        return {"exists": False, "size_mb": 0.0, "record_count": 0}

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM options")
        count = cursor.fetchone()[0]

        size_mb = DB_PATH.stat().st_size / (1024 * 1024)

        # Check for data age
        cursor.execute(
            "SELECT MIN(analysis_timestamp), MAX(analysis_timestamp) FROM options"
        )
        result = cursor.fetchone()
        oldest = result[0] if result[0] else None
        newest = result[1] if result[1] else None

        conn.close()

        return {
            "exists": True,
            "size_mb": round(size_mb, 2),
            "record_count": count,
            "oldest_record": oldest,
            "newest_record": newest,
        }

    except Exception as e:
        logger.error(f"❌ Failed to get DB stats: {e}")
        return {"exists": False, "size_mb": 0.0, "record_count": 0}
