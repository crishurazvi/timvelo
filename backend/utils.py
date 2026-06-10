import math
from urllib.parse import quote_plus


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in meters between two GPS coordinates."""
    radius_m = 6_371_000.0
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    delta_phi = math.radians(float(lat2) - float(lat1))
    delta_lambda = math.radians(float(lon2) - float(lon1))

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return radius_m * c


def format_distance(meters: float | int | None) -> str:
    if meters is None:
        return ""
    meters = float(meters)
    if meters < 1000:
        return f"{int(round(meters))} m"
    return f"{meters / 1000:.2f} km"


def make_google_maps_walking_url(origin_lat: float | None, origin_lon: float | None, dest_lat: float, dest_lon: float) -> str:
    if origin_lat is None or origin_lon is None:
        return make_google_maps_search_url(dest_lat, dest_lon)
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={origin_lat},{origin_lon}"
        f"&destination={dest_lat},{dest_lon}"
        "&travelmode=walking"
    )


def make_google_maps_search_url(lat: float, lon: float) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(f'{lat},{lon}')}"


def safe_int(value, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def safe_float(value, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default
