"""Shared constants and lightweight domain defaults for VeloTM Radar."""

import os

APP_NAME = "VeloTM Radar API"
DEFAULT_SOURCE_URL = os.getenv("VELOTM_URL", "http://www.velotm.ro/harta-statii-biciclete")
DEFAULT_LAT = 45.7489
DEFAULT_LON = 21.2087
TIMISOARA_CENTER = {"lat": DEFAULT_LAT, "lon": DEFAULT_LON}

ONLINE_STATUSES = {"Online", "Subpopulated", "Suprapopulated"}
RISK_STATUSES = {"Subpopulated", "Suprapopulated"}
OFFLINE_STATUS = "Offline"

SNAPSHOT_MIN_SECONDS = 300
SIGNIFICANT_CHANGE_THRESHOLD = 5
MAX_WALKING_DISTANCE_M = 800
