from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Point(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class RouteRequest(BaseModel):
    start: Point
    destination: Point


class Station(BaseModel):
    name: str
    address: str | None = None
    bikes_available: int
    empty_doors: int
    status: str
    latitude: float
    longitude: float
    capacity_estimated: int | None = None
    is_online: bool | None = None
    has_bikes: bool | None = None
    has_empty_doors: bool | None = None
    pickup_score: str | None = None
    return_score: str | None = None
    marker_color: str | None = None
    distance_m: float | None = None
    distance_label: str | None = None
    google_maps_url: str | None = None
    walking_google_maps_url: str | None = None


class Event(BaseModel):
    timestamp: str
    station_name: str
    event_type: str
    message: str
    old_value: str | None = None
    new_value: str | None = None


class StationsResponse(BaseModel):
    updated_at: str | None
    source_url: str
    warning: str | None = None
    stations: list[dict[str, Any]]
    metrics: dict[str, Any]
    nearest_bike_stations: list[dict[str, Any]] = []
    nearest_return_stations: list[dict[str, Any]] = []
    weather: dict[str, Any] | None = None
