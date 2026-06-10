from __future__ import annotations

import logging
import os
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from database import (
    db_ok,
    get_latest_snapshot,
    get_latest_timestamp,
    get_recent_events,
    get_station_history,
    init_db,
    save_events,
    save_snapshot,
    should_save_snapshot,
)
from models import APP_NAME, DEFAULT_LAT, DEFAULT_LON, DEFAULT_SOURCE_URL
from schemas import RouteRequest
from scraper import ScraperError, scrape_stations
from services import (
    add_distance_fields,
    calculate_metrics,
    calculate_route,
    detect_events,
    get_nearest_bike_stations,
    get_nearest_return_stations,
)
from weather import get_weather_with_score

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("velotm-radar")

SOURCE_URL = os.getenv("VELOTM_URL", DEFAULT_SOURCE_URL)
SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "10"))
PORT = int(os.getenv("PORT", "8000"))

cache_lock = threading.Lock()
state: dict[str, Any] = {
    "stations": [],
    "updated_at": None,
    "last_scrape_at": None,
    "last_error": None,
    "source_url": SOURCE_URL,
}

scheduler = BackgroundScheduler(timezone="UTC")


def _set_cache(stations: list[dict[str, Any]], warning: str | None = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with cache_lock:
        state["stations"] = stations
        state["updated_at"] = now
        state["last_scrape_at"] = now
        state["last_error"] = warning


def _get_cached_or_db_stations() -> list[dict[str, Any]]:
    with cache_lock:
        cached = list(state.get("stations") or [])
    if cached:
        return cached
    latest = get_latest_snapshot()
    if latest:
        with cache_lock:
            state["stations"] = latest
            state["updated_at"] = get_latest_timestamp()
        return latest
    return []


def scheduled_scrape_job(force_save: bool = False) -> dict[str, Any]:
    """Scrape VeloTM, detect changes, persist history, then refresh in-memory cache."""
    logger.info("Running VeloTM scrape job")
    previous = get_latest_snapshot()
    try:
        current = scrape_stations(SOURCE_URL)
        events = detect_events(previous, current)
        if force_save or should_save_snapshot(current, previous):
            save_snapshot(current)
        if events:
            save_events(events)
        _set_cache(current)
        return {"ok": True, "station_count": len(current), "events_count": len(events), "warning": None}
    except Exception as exc:
        logger.exception("Scrape job failed")
        fallback = previous or _get_cached_or_db_stations()
        warning = f"Scraper eșuat: {exc}. Returnez ultimele date valide, dacă există."
        if fallback:
            _set_cache(fallback, warning=warning)
        else:
            with cache_lock:
                state["last_error"] = warning
                state["last_scrape_at"] = datetime.now(timezone.utc).isoformat()
        return {"ok": False, "station_count": len(fallback), "events_count": 0, "warning": warning}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduled_scrape_job(force_save=True)
    scheduler.add_job(
        scheduled_scrape_job,
        "interval",
        minutes=SCRAPE_INTERVAL_MINUTES,
        id="velotm_scrape_job",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started, interval=%s minutes", SCRAPE_INTERVAL_MINUTES)
    yield
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")


app = FastAPI(title=APP_NAME, version="1.0.0", lifespan=lifespan)

# In producție, allow_origins se poate restrânge la domeniul frontend-ului Render.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "app": APP_NAME}


@app.get("/api/health")
def health() -> dict[str, Any]:
    stations = _get_cached_or_db_stations()
    with cache_lock:
        last_scrape_at = state.get("last_scrape_at")
        warning = state.get("last_error")
    return {
        "status": "ok" if stations else "degraded",
        "last_scrape_at": last_scrape_at,
        "station_count": len(stations),
        "db_ok": db_ok(),
        "warning": warning,
    }


@app.get("/api/stations")
def stations(
    lat: float | None = Query(None, ge=-90, le=90),
    lon: float | None = Query(None, ge=-180, le=180),
) -> dict[str, Any]:
    data = _get_cached_or_db_stations()
    if not data:
        raise HTTPException(status_code=503, detail="Nu există date VeloTM disponibile încă.")

    enriched = [add_distance_fields(s, lat, lon) for s in data] if lat is not None and lon is not None else [add_distance_fields(s, None, None) for s in data]
    nearest_bikes = get_nearest_bike_stations(data, lat, lon, n=3) if lat is not None and lon is not None else []
    nearest_returns = get_nearest_return_stations(data, lat, lon, n=3) if lat is not None and lon is not None else []
    weather = get_weather_with_score(lat or DEFAULT_LAT, lon or DEFAULT_LON)

    with cache_lock:
        updated_at = state.get("updated_at") or get_latest_timestamp()
        warning = state.get("last_error")

    return {
        "updated_at": updated_at,
        "source_url": SOURCE_URL,
        "warning": warning,
        "stations": enriched,
        "metrics": calculate_metrics(data),
        "nearest_bike_stations": nearest_bikes,
        "nearest_return_stations": nearest_returns,
        "weather": weather,
    }


@app.post("/api/route")
def route(payload: RouteRequest) -> dict[str, Any]:
    data = _get_cached_or_db_stations()
    if not data:
        raise HTTPException(status_code=503, detail="Nu există date VeloTM pentru calcularea traseului.")
    weather = get_weather_with_score(payload.start.lat, payload.start.lon)
    return calculate_route(
        data,
        start=payload.start.model_dump(),
        destination=payload.destination.model_dump(),
        weather_score=weather,
    )


@app.get("/api/history/{station_name}")
def history(station_name: str) -> list[dict[str, Any]]:
    return get_station_history(station_name)


@app.get("/api/events")
def events(limit: int = Query(20, ge=1, le=100)) -> list[dict[str, Any]]:
    return get_recent_events(limit=limit)


@app.get("/api/weather")
def weather(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON) -> dict[str, Any]:
    return get_weather_with_score(lat, lon)


@app.post("/api/refresh")
def refresh() -> dict[str, Any]:
    result = scheduled_scrape_job(force_save=True)
    if not result.get("ok") and result.get("station_count", 0) == 0:
        raise HTTPException(status_code=503, detail=result.get("warning") or "Refresh eșuat.")
    return {**result, **stations()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
