const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  if (!response.ok) {
    let message = `API error ${response.status}`;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch (_) {
      // keep default message
    }
    throw new Error(message);
  }
  return response.json();
}

export function getStations({ lat, lon } = {}) {
  const params = new URLSearchParams();
  if (lat !== undefined && lon !== undefined && lat !== null && lon !== null) {
    params.set("lat", lat);
    params.set("lon", lon);
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return request(`/api/stations${suffix}`);
}

export function refreshStations() {
  return request("/api/refresh", { method: "POST" });
}

export function getRoute(start, destination) {
  return request("/api/route", {
    method: "POST",
    body: JSON.stringify({ start, destination })
  });
}

export function getHistory(stationName) {
  return request(`/api/history/${encodeURIComponent(stationName)}`);
}

export function getEvents() {
  return request("/api/events");
}

export function getWeather(lat, lon) {
  const params = new URLSearchParams();
  if (lat !== undefined && lon !== undefined && lat !== null && lon !== null) {
    params.set("lat", lat);
    params.set("lon", lon);
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return request(`/api/weather${suffix}`);
}

export { API_BASE_URL };
