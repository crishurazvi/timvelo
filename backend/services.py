from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from models import (
    MAX_WALKING_DISTANCE_M,
    OFFLINE_STATUS,
    ONLINE_STATUSES,
    RISK_STATUSES,
    SIGNIFICANT_CHANGE_THRESHOLD,
)
from utils import format_distance, haversine_distance, make_google_maps_search_url, make_google_maps_walking_url


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_station_online(status: str | None) -> bool:
    return str(status or "").strip() in ONLINE_STATUSES


def calculate_pickup_score(station: dict[str, Any]) -> str:
    status = str(station.get("status") or station.get("Status") or "").strip()
    bikes = int(station.get("bikes_available", station.get("OcuppiedSpots", 0)) or 0)

    if status == OFFLINE_STATUS:
        return "Inutilă momentan"
    if bikes > 5:
        return "Excelentă pentru preluare"
    if 3 <= bikes <= 5:
        return "OK pentru preluare"
    if 1 <= bikes <= 2:
        return "Riscantă" if status not in RISK_STATUSES else "Riscantă, status instabil"
    return "Fără biciclete"


def calculate_return_score(station: dict[str, Any]) -> str:
    status = str(station.get("status") or station.get("Status") or "").strip()
    doors = int(station.get("empty_doors", station.get("EmptyDoors", 0)) or 0)

    if status == OFFLINE_STATUS:
        return "Inutilă momentan"
    if doors > 5:
        return "Excelentă pentru returnare"
    if 3 <= doors <= 5:
        return "OK pentru returnare"
    if 1 <= doors <= 2:
        return "Riscantă pentru returnare" if status not in RISK_STATUSES else "Riscantă, status instabil"
    return "Nu poți returna"


def calculate_marker_color(station: dict[str, Any]) -> str:
    status = str(station.get("status") or "").strip()
    bikes = int(station.get("bikes_available", 0) or 0)

    if not status:
        return "gray"
    if status == OFFLINE_STATUS:
        return "red"
    if status in RISK_STATUSES:
        return "orange"
    if bikes > 5:
        return "green"
    if 1 <= bikes <= 5:
        return "orange"
    if bikes == 0:
        return "red"
    return "gray"


def add_distance_fields(station: dict[str, Any], lat: float | None, lon: float | None) -> dict[str, Any]:
    enriched = dict(station)
    enriched["google_maps_url"] = make_google_maps_search_url(enriched["latitude"], enriched["longitude"])
    if lat is None or lon is None:
        return enriched
    distance = haversine_distance(lat, lon, enriched["latitude"], enriched["longitude"])
    enriched["distance_m"] = round(distance, 1)
    enriched["distance_label"] = format_distance(distance)
    enriched["walking_google_maps_url"] = make_google_maps_walking_url(lat, lon, enriched["latitude"], enriched["longitude"])
    return enriched


def station_pickup_sort_score(station: dict[str, Any], origin_lat: float, origin_lon: float) -> float:
    distance = haversine_distance(origin_lat, origin_lon, station["latitude"], station["longitude"])
    bikes = int(station.get("bikes_available", 0) or 0)
    risk_penalty = 250 if station.get("status") in RISK_STATUSES else 0
    low_bike_penalty = 250 if bikes == 1 else 80 if bikes == 2 else 0
    return distance + risk_penalty + low_bike_penalty


def station_return_sort_score(station: dict[str, Any], origin_lat: float, origin_lon: float) -> float:
    distance = haversine_distance(origin_lat, origin_lon, station["latitude"], station["longitude"])
    doors = int(station.get("empty_doors", 0) or 0)
    risk_penalty = 250 if station.get("status") in RISK_STATUSES else 0
    low_space_penalty = 250 if doors == 1 else 80 if doors == 2 else 0
    return distance + risk_penalty + low_space_penalty


def get_nearest_bike_stations(stations: list[dict[str, Any]], lat: float, lon: float, n: int = 3) -> list[dict[str, Any]]:
    valid = [s for s in stations if is_station_online(s.get("status")) and int(s.get("bikes_available", 0) or 0) > 0]
    valid.sort(key=lambda s: station_pickup_sort_score(s, lat, lon))
    return [add_distance_fields(s, lat, lon) for s in valid[:n]]


def get_nearest_return_stations(stations: list[dict[str, Any]], lat: float, lon: float, n: int = 3) -> list[dict[str, Any]]:
    valid = [s for s in stations if is_station_online(s.get("status")) and int(s.get("empty_doors", 0) or 0) > 0]
    valid.sort(key=lambda s: station_return_sort_score(s, lat, lon))
    return [add_distance_fields(s, lat, lon) for s in valid[:n]]


def get_best_pickup_station(stations: list[dict[str, Any]], lat: float, lon: float) -> dict[str, Any] | None:
    nearest = get_nearest_bike_stations(stations, lat, lon, n=1)
    return nearest[0] if nearest else None


def get_best_return_station(stations: list[dict[str, Any]], lat: float, lon: float) -> dict[str, Any] | None:
    nearest = get_nearest_return_stations(stations, lat, lon, n=1)
    return nearest[0] if nearest else None


def calculate_metrics(stations: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total_bikes": sum(int(s.get("bikes_available", 0) or 0) for s in stations),
        "total_empty_doors": sum(int(s.get("empty_doors", 0) or 0) for s in stations),
        "online_stations": sum(1 for s in stations if is_station_online(s.get("status"))),
        "offline_stations": sum(1 for s in stations if s.get("status") == OFFLINE_STATUS),
        "stations_without_bikes": sum(1 for s in stations if int(s.get("bikes_available", 0) or 0) == 0),
        "stations_without_empty_doors": sum(1 for s in stations if int(s.get("empty_doors", 0) or 0) == 0),
    }


def calculate_route(
    stations: list[dict[str, Any]],
    start: dict[str, float],
    destination: dict[str, float],
    weather_score: dict[str, Any] | None = None,
) -> dict[str, Any]:
    start_lat, start_lon = float(start["lat"]), float(start["lon"])
    dest_lat, dest_lon = float(destination["lat"]), float(destination["lon"])

    pickup = get_best_pickup_station(stations, start_lat, start_lon)
    dropoff = get_best_return_station(stations, dest_lat, dest_lon)

    reasons: list[str] = []
    worth_it = True

    if not pickup:
        worth_it = False
        reasons.append("Nu există stație validă de preluare lângă plecare.")
    if not dropoff:
        worth_it = False
        reasons.append("Nu există stație validă de returnare lângă destinație.")

    walk_to_pickup = None
    walk_from_return = None
    total_walking = None
    bike_distance = None

    if pickup:
        walk_to_pickup = haversine_distance(start_lat, start_lon, pickup["latitude"], pickup["longitude"])
        if walk_to_pickup > MAX_WALKING_DISTANCE_M:
            worth_it = False
            reasons.append(f"Stația de preluare este prea departe: {format_distance(walk_to_pickup)}.")

    if dropoff:
        walk_from_return = haversine_distance(dropoff["latitude"], dropoff["longitude"], dest_lat, dest_lon)
        if walk_from_return > MAX_WALKING_DISTANCE_M:
            worth_it = False
            reasons.append(f"Stația de returnare este prea departe de destinație: {format_distance(walk_from_return)}.")

    if pickup and dropoff:
        bike_distance = haversine_distance(pickup["latitude"], pickup["longitude"], dropoff["latitude"], dropoff["longitude"])
        total_walking = (walk_to_pickup or 0) + (walk_from_return or 0)

    if weather_score and weather_score.get("weather_available") is not False:
        score = int(weather_score.get("score", 10))
        if score <= 4:
            worth_it = False
            reasons.append("Vremea este nefavorabilă pentru bicicletă.")

    if not reasons:
        reasons.append("Merită VeloTM acum: stațiile sunt accesibile și există biciclete/locuri goale.")

    return {
        "worth_it": worth_it,
        "reason": " ".join(reasons),
        "reasons": reasons,
        "start": {"lat": start_lat, "lon": start_lon},
        "destination": {"lat": dest_lat, "lon": dest_lon},
        "pickup_station": pickup,
        "return_station": dropoff,
        "walk_to_pickup_m": round(walk_to_pickup, 1) if walk_to_pickup is not None else None,
        "walk_to_pickup_label": format_distance(walk_to_pickup) if walk_to_pickup is not None else None,
        "walk_from_return_m": round(walk_from_return, 1) if walk_from_return is not None else None,
        "walk_from_return_label": format_distance(walk_from_return) if walk_from_return is not None else None,
        "bike_distance_m": round(bike_distance, 1) if bike_distance is not None else None,
        "bike_distance_label": format_distance(bike_distance) if bike_distance is not None else None,
        "total_walking_m": round(total_walking, 1) if total_walking is not None else None,
        "total_walking_label": format_distance(total_walking) if total_walking is not None else None,
        "pickup_google_maps_url": make_google_maps_walking_url(start_lat, start_lon, pickup["latitude"], pickup["longitude"]) if pickup else None,
        "return_google_maps_url": make_google_maps_walking_url(dropoff["latitude"], dropoff["longitude"], dest_lat, dest_lon) if dropoff else None,
    }


def detect_events(previous_stations: list[dict[str, Any]], current_stations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not previous_stations or not current_stations:
        return []

    previous = {s["name"]: s for s in previous_stations if s.get("name")}
    events: list[dict[str, Any]] = []
    ts = now_iso()

    for curr in current_stations:
        name = curr.get("name")
        if not name or name not in previous:
            continue
        prev = previous[name]

        prev_bikes = int(prev.get("bikes_available", 0) or 0)
        curr_bikes = int(curr.get("bikes_available", 0) or 0)
        prev_doors = int(prev.get("empty_doors", 0) or 0)
        curr_doors = int(curr.get("empty_doors", 0) or 0)
        prev_status = str(prev.get("status") or "")
        curr_status = str(curr.get("status") or "")

        def add(event_type: str, message: str, old_value: Any, new_value: Any):
            events.append(
                {
                    "timestamp": ts,
                    "station_name": name,
                    "event_type": event_type,
                    "message": message,
                    "old_value": str(old_value),
                    "new_value": str(new_value),
                }
            )

        if prev_status != curr_status:
            if prev_status == OFFLINE_STATUS and curr_status != OFFLINE_STATUS:
                add("station_online", f"Stația {name} a devenit online", prev_status, curr_status)
            elif prev_status != OFFLINE_STATUS and curr_status == OFFLINE_STATUS:
                add("station_offline", f"Stația {name} a devenit offline", prev_status, curr_status)
            else:
                add("status_changed", f"Stația {name} și-a schimbat statusul: {prev_status} → {curr_status}", prev_status, curr_status)

        if prev_bikes == 0 and curr_bikes > 0:
            add("bikes_appeared", f"A apărut bicicletă la {name}: 0 → {curr_bikes}", prev_bikes, curr_bikes)
        elif prev_bikes > 0 and curr_bikes == 0:
            add("bikes_empty", f"Stația {name} s-a golit: {prev_bikes} → 0 biciclete", prev_bikes, curr_bikes)
        elif curr_bikes - prev_bikes >= SIGNIFICANT_CHANGE_THRESHOLD:
            add("bikes_increased", f"Au apărut mai multe biciclete la {name}: {prev_bikes} → {curr_bikes}", prev_bikes, curr_bikes)
        elif prev_bikes - curr_bikes >= SIGNIFICANT_CHANGE_THRESHOLD:
            add("bikes_decreased", f"S-au luat multe biciclete de la {name}: {prev_bikes} → {curr_bikes}", prev_bikes, curr_bikes)

        if prev_doors == 0 and curr_doors > 0:
            add("empty_doors_appeared", f"Acum poți returna bicicleta la {name}: 0 → {curr_doors} locuri goale", prev_doors, curr_doors)
        elif prev_doors > 0 and curr_doors == 0:
            add("empty_doors_full", f"Nu mai poți returna la {name}: {prev_doors} → 0 locuri goale", prev_doors, curr_doors)
        elif curr_doors - prev_doors >= SIGNIFICANT_CHANGE_THRESHOLD:
            add("empty_doors_increased", f"Au apărut locuri goale la {name}: {prev_doors} → {curr_doors}", prev_doors, curr_doors)
        elif prev_doors - curr_doors >= SIGNIFICANT_CHANGE_THRESHOLD:
            add("empty_doors_decreased", f"S-au ocupat multe locuri la {name}: {prev_doors} → {curr_doors}", prev_doors, curr_doors)

    return events[:50]
