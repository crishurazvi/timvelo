import { divIcon } from "leaflet";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import { useEffect, useMemo, useState } from "react";
import { markerClass } from "../utils/stationScore";
import { makeSearchUrl, makeWalkingUrl } from "../utils/googleMaps";

const DEFAULT_CENTER = [45.7489, 21.2087];

function Recenter({ position }) {
  const map = useMap();
  useEffect(() => {
    if (position) map.setView([position.lat, position.lon], 15);
  }, [map, position]);
  return null;
}

function stationIcon(station) {
  return divIcon({
    className: "station-div-icon",
    html: `<div class="station-marker ${markerClass(station.marker_color)}"><span>${station.bikes_available}</span></div>`,
    iconSize: [36, 36],
    iconAnchor: [18, 18]
  });
}

function userIcon() {
  return divIcon({
    className: "user-div-icon",
    html: `<div class="user-marker"></div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12]
  });
}

export default function StationMap({ stations = [], userPosition, favorites = [], onToggleFavorite }) {
  const [filter, setFilter] = useState("all");
  const center = userPosition ? [userPosition.lat, userPosition.lon] : DEFAULT_CENTER;
  const favoriteSet = useMemo(() => new Set(favorites), [favorites]);

  const filtered = useMemo(() => {
    return stations.filter((s) => {
      if (filter === "bikes") return s.bikes_available > 0;
      if (filter === "returns") return s.empty_doors > 0;
      if (filter === "online") return s.is_online;
      if (filter === "favorites") return favoriteSet.has(s.name);
      return true;
    });
  }, [stations, filter, favoriteSet]);

  return (
    <div className="overflow-hidden rounded-3xl border border-white/10 bg-app-card">
      <div className="flex gap-2 overflow-x-auto p-3">
        {[
          ["all", "Toate"],
          ["bikes", "Cu biciclete"],
          ["returns", "Cu locuri"],
          ["online", "Online"],
          ["favorites", "Favorite"]
        ].map(([id, label]) => (
          <button key={id} onClick={() => setFilter(id)} className={`whitespace-nowrap rounded-full px-3 py-2 text-xs font-bold ${filter === id ? "bg-app-cyan text-slate-950" : "bg-white/10 text-slate-300"}`}>
            {label}
          </button>
        ))}
      </div>
      <MapContainer center={center} zoom={14} className="h-[560px] w-full" scrollWheelZoom>
        <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <Recenter position={userPosition} />
        {userPosition ? <Marker position={[userPosition.lat, userPosition.lon]} icon={userIcon()}><Popup>Locația ta</Popup></Marker> : null}
        {filtered.map((station) => {
          const destination = { lat: station.latitude, lon: station.longitude };
          return (
            <Marker key={station.name} position={[station.latitude, station.longitude]} icon={stationIcon(station)}>
              <Popup>
                <div className="w-56 text-slate-900">
                  <strong>{station.name}</strong>
                  <p>{station.address}</p>
                  <p>🚲 {station.bikes_available} biciclete · 🔓 {station.empty_doors} locuri</p>
                  <p>Status: {station.status}</p>
                  <p>{station.pickup_score}</p>
                  {station.distance_label ? <p>Distanță: {station.distance_label}</p> : null}
                  <div className="mt-2 grid gap-1">
                    <a href={makeSearchUrl(destination)} target="_blank" rel="noreferrer">Deschide în Google Maps</a>
                    {userPosition ? <a href={makeWalkingUrl(userPosition, destination)} target="_blank" rel="noreferrer">Traseu pe jos</a> : null}
                    {onToggleFavorite ? <button onClick={() => onToggleFavorite(station.name)}>{favoriteSet.has(station.name) ? "Scoate din favorite" : "Adaugă la favorite"}</button> : null}
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}
