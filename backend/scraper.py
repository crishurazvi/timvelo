from __future__ import annotations

import json
import os
import re
from typing import Any

import requests
from bs4 import BeautifulSoup

from models import DEFAULT_SOURCE_URL
from services import calculate_marker_color, calculate_pickup_score, calculate_return_score, is_station_online
from utils import safe_float, safe_int

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36 VeloTMRadar/1.0"
    )
}


class ScraperError(RuntimeError):
    pass


def fetch_velotm_page(url: str = DEFAULT_SOURCE_URL) -> str:
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=15)
        response.raise_for_status()
        return response.text
    except requests.Timeout as exc:
        raise ScraperError("Timeout la descărcarea paginii VeloTM.") from exc
    except requests.HTTPError as exc:
        raise ScraperError(f"Răspuns HTTP invalid de la VeloTM: {exc.response.status_code}.") from exc
    except requests.RequestException as exc:
        raise ScraperError(f"Nu s-a putut descărca pagina VeloTM: {exc}.") from exc


def _extract_bracketed_array(source: str, start_index: int) -> str:
    array_start = source.find("[", start_index)
    if array_start == -1:
        raise ScraperError("Array-ul items nu conține '['.")

    depth = 0
    in_string = False
    escape = False
    quote_char = ""

    for idx in range(array_start, len(source)):
        char = source[idx]

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote_char:
                in_string = False
            continue

        if char in {"'", '"'}:
            in_string = True
            quote_char = char
            continue
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return source[array_start : idx + 1]

    raise ScraperError("Array-ul items este incomplet sau invalid.")


def _strip_js_comments(value: str) -> str:
    value = re.sub(r"/\*.*?\*/", "", value, flags=re.DOTALL)
    value = re.sub(r"(?<!:)//.*", "", value)
    return value


def _coerce_js_array_to_json(value: str) -> str:
    value = _strip_js_comments(value).strip()
    value = re.sub(r",\s*([}\]])", r"\1", value)
    # Fallback for rare JS-like objects with unquoted keys.
    value = re.sub(r"([{,])\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1 "\2":', value)
    return value


def extract_items_array(html: str) -> list[dict[str, Any]]:
    if not html:
        raise ScraperError("Pagina VeloTM este goală.")

    soup = BeautifulSoup(html, "html.parser")
    scripts = "\n".join(script.get_text("\n") for script in soup.find_all("script"))
    source = scripts or html

    show_stations_index = source.find("showStations")
    search_from = show_stations_index if show_stations_index != -1 else 0

    match = re.search(r"var\s+items\s*=", source[search_from:], flags=re.IGNORECASE)
    if not match:
        # Retry over entire HTML because some deployments minify or move the array.
        match = re.search(r"var\s+items\s*=", source, flags=re.IGNORECASE)
        search_from = 0
    if not match:
        raise ScraperError("Nu am găsit `var items = [...]` în pagina VeloTM.")

    assignment_index = search_from + match.end()
    raw_array = _extract_bracketed_array(source, assignment_index)
    json_text = _coerce_js_array_to_json(raw_array)

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ScraperError(f"Array-ul `items` există, dar JSON-ul nu poate fi parsat: {exc}.") from exc

    if not isinstance(data, list):
        raise ScraperError("`items` nu este o listă.")
    return [item for item in data if isinstance(item, dict)]


def normalize_station(raw: dict[str, Any]) -> dict[str, Any]:
    name = str(raw.get("StationName") or raw.get("name") or "Stație necunoscută").strip()
    address = str(raw.get("Address") or raw.get("address") or "").strip()
    bikes = safe_int(raw.get("OcuppiedSpots", raw.get("bikes_available", 0)), 0)
    empty_doors = safe_int(raw.get("EmptyDoors", raw.get("empty_doors", 0)), 0)
    status = str(raw.get("Status") or raw.get("status") or "Unknown").strip()
    latitude = safe_float(raw.get("Latitude", raw.get("latitude")))
    longitude = safe_float(raw.get("Longitude", raw.get("longitude")))

    if latitude is None or longitude is None:
        raise ScraperError(f"Coordonate lipsă pentru stația {name}.")

    station = {
        "name": name,
        "address": address,
        "bikes_available": bikes,
        "empty_doors": empty_doors,
        "status": status,
        "latitude": latitude,
        "longitude": longitude,
    }
    station.update(
        {
            "capacity_estimated": bikes + empty_doors,
            "is_online": is_station_online(status),
            "has_bikes": bikes > 0,
            "has_empty_doors": empty_doors > 0,
            "pickup_score": calculate_pickup_score(station),
            "return_score": calculate_return_score(station),
            "marker_color": calculate_marker_color(station),
        }
    )
    return station


def scrape_stations(url: str | None = None) -> list[dict[str, Any]]:
    source_url = url or os.getenv("VELOTM_URL", DEFAULT_SOURCE_URL)
    html = fetch_velotm_page(source_url)
    raw_items = extract_items_array(html)

    stations: list[dict[str, Any]] = []
    errors: list[str] = []
    for raw in raw_items:
        try:
            stations.append(normalize_station(raw))
        except Exception as exc:
            errors.append(str(exc))

    if not stations:
        details = "; ".join(errors[:3]) if errors else "niciun item valid"
        raise ScraperError(f"Nu am putut normaliza nicio stație VeloTM: {details}.")

    return stations
