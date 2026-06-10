from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

from models import DEFAULT_LAT, DEFAULT_LON

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_weather(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON) -> dict[str, Any]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,is_day,precipitation,weather_code,wind_speed_10m",
        "daily": "sunset",
        "timezone": "auto",
        "forecast_days": 1,
    }
    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=8)
        response.raise_for_status()
        payload = response.json()
        current = payload.get("current") or {}
        daily = payload.get("daily") or {}
        return {
            "weather_available": True,
            "timestamp": current.get("time") or datetime.now(timezone.utc).isoformat(),
            "temperature": current.get("temperature_2m"),
            "wind_speed": current.get("wind_speed_10m"),
            "precipitation": current.get("precipitation"),
            "weather_code": current.get("weather_code"),
            "is_day": current.get("is_day"),
            "sunset": (daily.get("sunset") or [None])[0] if isinstance(daily.get("sunset"), list) else None,
            "raw_provider": "Open-Meteo",
        }
    except Exception as exc:
        return {
            "weather_available": False,
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_provider": "Open-Meteo",
        }


def calculate_bike_weather_score(weather: dict[str, Any]) -> dict[str, Any]:
    if not weather or weather.get("weather_available") is False:
        return {
            "weather_available": False,
            "score": None,
            "label": "Date meteo indisponibile",
            "reason": "Datele meteo nu sunt disponibile momentan.",
        }

    temp = weather.get("temperature")
    wind = weather.get("wind_speed")
    precipitation = weather.get("precipitation")
    code = weather.get("weather_code")
    is_day = weather.get("is_day")

    temp = float(temp) if temp is not None else 20.0
    wind = float(wind) if wind is not None else 0.0
    precipitation = float(precipitation) if precipitation is not None else 0.0
    code = int(code) if code is not None else 0

    score = 10
    reasons: list[str] = []

    if precipitation >= 4:
        score -= 5
        reasons.append("precipitații importante")
    elif precipitation > 0:
        score -= 3
        reasons.append("ploaie prezentă")

    rainy_codes = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}
    storm_codes = {95, 96, 99}
    snow_codes = {71, 73, 75, 77, 85, 86}
    if code in storm_codes:
        score -= 6
        reasons.append("risc de furtună")
    elif code in snow_codes:
        score -= 6
        reasons.append("ninsoare")
    elif code in rainy_codes and precipitation == 0:
        score -= 2
        reasons.append("cod meteo de ploaie")

    if wind >= 35:
        score -= 4
        reasons.append("vânt puternic")
    elif wind >= 20:
        score -= 2
        reasons.append("vânt moderat")

    if temp < 5:
        score -= 4
        reasons.append("temperatură foarte joasă")
    elif temp < 12:
        score -= 2
        reasons.append("răcoare")
    elif temp > 35:
        score -= 4
        reasons.append("temperatură foarte ridicată")
    elif temp > 30:
        score -= 2
        reasons.append("cald")

    if is_day == 0:
        score -= 2
        reasons.append("este noapte")

    score = max(0, min(10, int(round(score))))
    if score >= 8:
        label = "Excelent pentru bicicletă"
    elif score >= 5:
        label = "Acceptabil"
    else:
        label = "Mai bine nu"

    if not reasons:
        reason = "Vreme uscată, temperatură bună, vânt slab."
    else:
        reason = "Atenție la " + ", ".join(reasons) + "."

    return {
        "weather_available": True,
        "score": score,
        "label": label,
        "reason": reason,
        "temperature": temp,
        "wind_speed": wind,
        "precipitation": precipitation,
        "weather_code": code,
        "is_day": is_day,
        "sunset": weather.get("sunset"),
        "timestamp": weather.get("timestamp"),
    }


def get_weather_with_score(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON) -> dict[str, Any]:
    weather = fetch_weather(lat, lon)
    score = calculate_bike_weather_score(weather)
    return {**weather, **score}
