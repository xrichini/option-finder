#!/usr/bin/env python3
"""
api/daemon_endpoints.py — Endpoints FastAPI pour le scan daemon

Expose les résultats pré-calculés par scan_daemon.py (data/latest_scan.json).
Le frontend peut appeler GET /api/daemon/latest-scan pour afficher
instantanément les résultats sans déclencher de scan.

Endpoints:
    GET /api/daemon/latest-scan   Retourne le dernier résultat du daemon
    GET /api/daemon/status        Statut du daemon (âge, count, université…)
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
from datetime import datetime, timezone
import json
import logging

logger = logging.getLogger(__name__)

daemon_router = APIRouter(prefix="/api/daemon", tags=["Scan Daemon"])

_SCAN_FILE = Path("data/latest_scan.json")


# ── Helper ────────────────────────────────────────────────────────────────────

def _read_scan_file() -> dict:
    """Lit et parse data/latest_scan.json. Lève HTTPException si absent/illisible."""
    if not _SCAN_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "Aucun résultat de scan disponible. "
                "Lance scan_daemon.py pour générer les résultats."
            ),
        )
    try:
        return json.loads(_SCAN_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur de lecture du fichier de scan: {exc}",
        )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@daemon_router.get("/latest-scan")
async def get_latest_daemon_scan():
    """
    Retourne le dernier résultat du scan daemon (data/latest_scan.json).

    Format de réponse identique à POST /api/hybrid/screen/scan-all pour que
    le frontend puisse afficher les résultats avec le même code.

    Returns 404 si aucun scan n'a encore été effectué.
    """
    payload = _read_scan_file()

    # Ajoute l'âge du scan dans la réponse
    try:
        ts = datetime.fromisoformat(payload.get("timestamp", ""))
        age_s = (datetime.now() - ts).total_seconds()
        payload["age_seconds"] = round(age_s)
        payload["age_minutes"] = round(age_s / 60, 1)
    except Exception:
        pass

    logger.info(
        f"📤 /api/daemon/latest-scan → "
        f"{payload.get('total_count', 0)} opportunités "
        f"(universe: {payload.get('universe', '?')})"
    )
    return payload


@daemon_router.get("/status")
async def get_daemon_status():
    """
    Statut du scan daemon: fichier présent? âge? nombre de résultats?

    Champ 'stale' = True si le dernier scan date de plus d'1 heure.
    """
    if not _SCAN_FILE.exists():
        return {
            "available": False,
            "message": "data/latest_scan.json introuvable. daemon pas encore lancé?",
            "file": str(_SCAN_FILE),
        }

    stat = _SCAN_FILE.stat()
    mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    age_s = (datetime.now(tz=timezone.utc) - mtime).total_seconds()

    try:
        payload = json.loads(_SCAN_FILE.read_text(encoding="utf-8"))
        ts        = payload.get("timestamp", "unknown")
        count     = payload.get("total_count", 0)
        universe  = payload.get("universe", "unknown")
        sym_count = payload.get("symbols_count", 0)
    except Exception:
        ts, count, universe, sym_count = "parse_error", 0, "unknown", 0

    return {
        "available":           True,
        "file":                str(_SCAN_FILE),
        "last_scan":           ts,
        "age_seconds":         round(age_s),
        "age_minutes":         round(age_s / 60, 1),
        "opportunities_count": count,
        "universe":            universe,
        "symbols_count":       sym_count,
        "stale":               age_s > 3600,   # avertissement si > 1h
    }
