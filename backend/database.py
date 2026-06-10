from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any

from dateutil import parser as dt_parser

from models import SNAPSHOT_MIN_SECONDS

DB_PATH = os.getenv("DB_PATH", "history.sqlite")
_DB_LOCK = threading.Lock()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _DB_LOCK:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS station_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    station_name TEXT,
                    address TEXT,
                    bikes_available INTEGER,
                    empty_doors INTEGER,
                    status TEXT,
                    latitude REAL,
                    longitude REAL
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp
                ON station_snapshots(timestamp)
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_snapshots_station
                ON station_snapshots(station_name)
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    station_name TEXT,
                    event_type TEXT,
                    message TEXT,
                    old_value TEXT,
                    new_value TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_events_timestamp
                ON events(timestamp)
                """
            )
            conn.commit()
        finally:
            conn.close()


def db_ok() -> bool:
    try:
        init_db()
        with get_connection() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


def _row_to_station(row: sqlite3.Row) -> dict[str, Any]:
    bikes = int(row["bikes_available"] or 0)
    empty = int(row["empty_doors"] or 0)
    status = str(row["status"] or "Unknown")
    station = {
        "name": row["station_name"],
        "address": row["address"],
        "bikes_available": bikes,
        "empty_doors": empty,
        "status": status,
        "latitude": float(row["latitude"]),
        "longitude": float(row["longitude"]),
        "capacity_estimated": bikes + empty,
        "is_online": status != "Offline",
        "has_bikes": bikes > 0,
        "has_empty_doors": empty > 0,
    }
    # Recompute volatile UI fields lazily to keep DB schema simple.
    from services import calculate_marker_color, calculate_pickup_score, calculate_return_score

    station["pickup_score"] = calculate_pickup_score(station)
    station["return_score"] = calculate_return_score(station)
    station["marker_color"] = calculate_marker_color(station)
    return station


def get_latest_timestamp() -> str | None:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT MAX(timestamp) AS ts FROM station_snapshots").fetchone()
        return row["ts"] if row and row["ts"] else None


def save_snapshot(stations: list[dict[str, Any]]) -> None:
    if not stations:
        return
    init_db()
    timestamp = datetime.now(timezone.utc).isoformat()
    with _DB_LOCK:
        conn = get_connection()
        try:
            conn.executemany(
                """
                INSERT INTO station_snapshots
                (timestamp, station_name, address, bikes_available, empty_doors, status, latitude, longitude)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        timestamp,
                        s.get("name"),
                        s.get("address"),
                        int(s.get("bikes_available", 0) or 0),
                        int(s.get("empty_doors", 0) or 0),
                        s.get("status"),
                        float(s.get("latitude")),
                        float(s.get("longitude")),
                    )
                    for s in stations
                ],
            )
            conn.commit()
        finally:
            conn.close()


def get_latest_snapshot() -> list[dict[str, Any]]:
    init_db()
    ts = get_latest_timestamp()
    if not ts:
        return []
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM station_snapshots
            WHERE timestamp = ?
            ORDER BY station_name ASC
            """,
            (ts,),
        ).fetchall()
    return [_row_to_station(row) for row in rows]


def get_previous_snapshot() -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT timestamp FROM station_snapshots
            GROUP BY timestamp
            ORDER BY timestamp DESC
            LIMIT 1 OFFSET 1
            """
        ).fetchone()
        if not row:
            return []
        rows = conn.execute(
            """
            SELECT * FROM station_snapshots
            WHERE timestamp = ?
            ORDER BY station_name ASC
            """,
            (row["timestamp"],),
        ).fetchall()
    return [_row_to_station(r) for r in rows]


def get_station_history(station_name: str) -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT timestamp, station_name, bikes_available, empty_doors, status
            FROM station_snapshots
            WHERE station_name = ?
            ORDER BY timestamp ASC
            """,
            (station_name,),
        ).fetchall()
    return [dict(row) for row in rows]


def save_events(events: list[dict[str, Any]]) -> None:
    if not events:
        return
    init_db()
    with _DB_LOCK:
        conn = get_connection()
        try:
            conn.executemany(
                """
                INSERT INTO events (timestamp, station_name, event_type, message, old_value, new_value)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        e.get("timestamp"),
                        e.get("station_name"),
                        e.get("event_type"),
                        e.get("message"),
                        e.get("old_value"),
                        e.get("new_value"),
                    )
                    for e in events
                ],
            )
            conn.commit()
        finally:
            conn.close()


def get_recent_events(limit: int = 20) -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT timestamp, station_name, event_type, message, old_value, new_value
            FROM events
            ORDER BY datetime(timestamp) DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def _compact_signature(stations: list[dict[str, Any]]) -> str:
    compact = sorted(
        (
            s.get("name"),
            int(s.get("bikes_available", 0) or 0),
            int(s.get("empty_doors", 0) or 0),
            s.get("status"),
        )
        for s in stations
    )
    return json.dumps(compact, sort_keys=True, ensure_ascii=False)


def should_save_snapshot(current: list[dict[str, Any]], previous: list[dict[str, Any]]) -> bool:
    if not current:
        return False
    if not previous:
        return True

    if _compact_signature(current) != _compact_signature(previous):
        return True

    last_ts = get_latest_timestamp()
    if not last_ts:
        return True
    try:
        elapsed = (datetime.now(timezone.utc) - dt_parser.parse(last_ts)).total_seconds()
    except Exception:
        return True
    return elapsed >= SNAPSHOT_MIN_SECONDS
