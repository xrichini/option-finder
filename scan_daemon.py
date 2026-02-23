#!/usr/bin/env python3
"""
scan_daemon.py — Scanner continu pour déploiement sur VM

Lance des scans réguliers pendant les heures de marché US et écrit les
résultats dans data/latest_scan.json.  Le serveur FastAPI (app.py) expose
ensuite ce fichier via GET /api/daemon/latest-scan pour que le frontend
affiche les résultats instantanément sans attendre un nouveau scan.

Utilisation:
    python scan_daemon.py                                   # nasdaq100, toutes les 15 min
    python scan_daemon.py --universe sp500  --interval 20
    python scan_daemon.py --universe dow30  --interval 10
    python scan_daemon.py --once                            # un seul scan puis quitter
    python scan_daemon.py --once --force                    # scan hors heures de marché

Options avancées:
    --max-dte    <int>    Durée max avant expiration (défaut: 7)
    --min-volume <int>    Volume minimum             (défaut: 500)
    --min-oi     <int>    Open Interest minimum      (défaut: 100)
    --min-score  <float>  Whale score minimum        (défaut: 30.0)
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, time as dtime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("scan_daemon.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("scan_daemon")

# ── Constants ─────────────────────────────────────────────────────────────────
try:
    from zoneinfo import ZoneInfo          # Python 3.9+
    MARKET_TZ = ZoneInfo("America/New_York")
except ImportError:
    from dateutil.tz import gettz          # fallback: pip install python-dateutil
    MARKET_TZ = gettz("America/New_York")

MARKET_OPEN  = dtime(9, 30)
MARKET_CLOSE = dtime(16, 0)

DEFAULT_UNIVERSE = "nasdaq100"
DEFAULT_INTERVAL = 15  # minutes

OUTPUT_PATH = Path("data/latest_scan.json")

# ── Market hours ──────────────────────────────────────────────────────────────

def is_market_open() -> bool:
    """True si l'heure actuelle ET est dans les heures de marché (lun-ven)."""
    now_et = datetime.now(MARKET_TZ)
    if now_et.weekday() >= 5:   # samedi=5, dimanche=6
        return False
    t = now_et.time()
    return MARKET_OPEN <= t <= MARKET_CLOSE


# ── Universe resolution ───────────────────────────────────────────────────────

def fetch_symbols(universe: str) -> list:
    """
    Résout la liste de symboles pour l'univers donné.
    Utilise la logique existante (FMP → Wikipedia fallback, cache 24h).
    """
    from api.universe_endpoints import _fetch_universe
    symbols, source = _fetch_universe(universe)
    logger.info(f"📋 Universe {universe}: {len(symbols)} symboles (source: {source})")
    return symbols


# ── Async scan core ───────────────────────────────────────────────────────────

async def run_scan_async(symbols: list, params: dict) -> list:
    """
    Exécute un scan hybride complet et retourne la liste des opportunités.
    Instancie un nouveau HybridScreeningService (thread-safe, event-loop vierge).
    """
    from services.hybrid_screening_service import HybridScreeningService
    service = HybridScreeningService()

    async def _progress(current: int, total: int, symbol: str, details: str):
        if total > 0 and current % 20 == 0 and current > 0:
            pct = int(current / total * 100)
            logger.info(f"  ⏳ {current}/{total} ({pct}%) — {symbol}")

    logger.info(
        f"🔍 Lancement du scan: {len(symbols)} symboles | "
        f"max_dte={params['max_dte']}, min_vol={params['min_volume']}, "
        f"min_oi={params['min_oi']}, min_score={params['min_whale_score']}"
    )

    opportunities = await service.screen_options_hybrid(
        symbols=symbols,
        option_type="both",
        max_dte=params["max_dte"],
        min_volume=params["min_volume"],
        min_oi=params["min_oi"],
        min_whale_score=params["min_whale_score"],
        enable_ai=False,
        progress_callback=_progress,
    )

    return opportunities


# ── Result persistence ────────────────────────────────────────────────────────

def write_results(opportunities: list, universe: str, symbols: list):
    """
    Écrit les résultats dans data/latest_scan.json (écriture atomique).
    Le fichier est lu par le endpoint GET /api/daemon/latest-scan.
    """
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "universe": universe,
        "symbols_count": len(symbols),
        "total_count": len(opportunities),
        "opportunities": opportunities,
        "scan_type": "DAEMON_SCAN",
    }

    # Écriture atomique via fichier temporaire + rename
    tmp = OUTPUT_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, default=str), encoding="utf-8")
    tmp.replace(OUTPUT_PATH)

    calls = sum(1 for o in opportunities if o.get("option_type") == "CALL")
    puts  = len(opportunities) - calls
    logger.info(
        f"💾 Résultats sauvegardés → {OUTPUT_PATH}  "
        f"({len(opportunities)} total — {calls} CALLS, {puts} PUTS)"
    )


# ── Full scan cycle ───────────────────────────────────────────────────────────

def do_scan(universe: str, params: dict):
    """
    Cycle complet: résolution des symboles + scan + sauvegarde.
    Bloquant (utilise asyncio.run pour exécuter la partie async).
    """
    start = datetime.now()
    logger.info(f"{'='*60}")
    logger.info(f"🚀 Démarrage du scan — {start:%Y-%m-%d %H:%M:%S}")

    try:
        symbols = fetch_symbols(universe)
        if not symbols:
            logger.error("❌ Aucun symbole résolu, scan annulé.")
            return

        opportunities = asyncio.run(run_scan_async(symbols, params))
        write_results(opportunities, universe, symbols)

        elapsed = (datetime.now() - start).total_seconds()
        logger.info(
            f"✅ Scan terminé en {elapsed:.0f}s — "
            f"{len(opportunities)} opportunités trouvées."
        )

    except Exception:
        logger.error("❌ Erreur pendant le scan", exc_info=True)


# ── Scheduler job ─────────────────────────────────────────────────────────────

def scheduled_job(universe: str, params: dict, force: bool = False):
    """
    Job exécuté par APScheduler.
    Ignore les déclenchements hors heures de marché sauf si --force.
    """
    if not force and not is_market_open():
        now_et = datetime.now(MARKET_TZ)
        logger.info(f"💤 Marché fermé ({now_et:%H:%M ET, %A}) — scan ignoré.")
        return
    do_scan(universe, params)


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Squeeze Finder — scan daemon",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--universe",
        choices=["sp500", "nasdaq100", "dow30"],
        default=DEFAULT_UNIVERSE,
        help="Univers à scanner",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL,
        metavar="MINUTES",
        help="Intervalle entre les scans (minutes)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Effectuer un seul scan puis quitter",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Scanner même hors heures de marché (test/debug)",
    )
    # Scan parameters
    parser.add_argument("--max-dte",    type=int,   default=7,    help="DTE maximum")
    parser.add_argument("--min-volume", type=int,   default=500,  help="Volume minimum")
    parser.add_argument("--min-oi",     type=int,   default=100,  help="Open Interest minimum")
    parser.add_argument("--min-score",  type=float, default=30.0, help="Whale score minimum")

    args = parser.parse_args()

    params = {
        "max_dte":        args.max_dte,
        "min_volume":     args.min_volume,
        "min_oi":         args.min_oi,
        "min_whale_score": args.min_score,
    }

    logger.info(
        f"🛠️  Config: universe={args.universe}, interval={args.interval}m, "
        f"once={args.once}, force={args.force}"
    )
    logger.info(f"   Params: {params}")

    # ── Mode one-shot ──────────────────────────────────────────────────────────
    if args.once:
        if not args.force and not is_market_open():
            logger.warning(
                "⚠️  Marché fermé. Utilise --force pour scanner quand même."
            )
            # On scanne quand même en mode --once pour ne pas bloquer les tests
        do_scan(args.universe, params)
        return

    # ── Mode daemon (APScheduler) ──────────────────────────────────────────────
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
    except ImportError:
        logger.error(
            "❌ APScheduler introuvable. Installe-le: pip install apscheduler"
        )
        sys.exit(1)

    scheduler = BlockingScheduler(timezone=MARKET_TZ)
    scheduler.add_job(
        scheduled_job,
        trigger="interval",
        minutes=args.interval,
        id="scan_job",
        kwargs={
            "universe": args.universe,
            "params":   params,
            "force":    args.force,
        },
        next_run_time=datetime.now(MARKET_TZ),  # premier scan immédiat au démarrage
    )

    logger.info(
        f"⏰ Daemon démarré — scan toutes les {args.interval} min "
        f"(heures de marché ET, lun-ven 9h30-16h00)."
    )
    logger.info("   Ctrl+C pour arrêter.")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("🛑 Daemon arrêté proprement.")


if __name__ == "__main__":
    main()
