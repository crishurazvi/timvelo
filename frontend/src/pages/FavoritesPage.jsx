import { useState } from "react";
import FavoriteStations from "../components/FavoriteStations";
import LocationPickerMap from "../components/LocationPickerMap";
import StationCard from "../components/StationCard";
import { haversineDistance, formatDistance } from "../utils/distance";

const POINT_NAMES = ["ACASĂ", "SPITAL", "CENTRU", "GARĂ", "FACULTATE", "IULIUS TOWN", "CUSTOM"];

export default function FavoritesPage({ stations, favorites, onToggleFavorite, userPosition, personalPoints, setPersonalPoints }) {
  const [pointName, setPointName] = useState("ACASĂ");

  function savePoint(point) {
    setPersonalPoints({ ...personalPoints, [pointName]: point });
  }

  return (
    <div className="space-y-5">
      <section className="rounded-3xl bg-app-card p-5">
        <h2 className="text-2xl font-black">Favorite</h2>
        <p className="mt-1 text-sm text-slate-400">Stațiile și punctele personale rămân în localStorage, deci nu ai nevoie de cont.</p>
      </section>

      <FavoriteStations stations={stations} favorites={favorites} userPosition={userPosition} onToggleFavorite={onToggleFavorite} />

      <section className="space-y-3">
        <h3 className="text-xl font-black">Punctele mele</h3>
        <div className="rounded-3xl bg-app-card p-4">
          <select value={pointName} onChange={(e) => setPointName(e.target.value)} className="mb-3 w-full rounded-2xl bg-app-soft p-3 text-white">
            {POINT_NAMES.map((name) => <option key={name} value={name}>{name}</option>)}
          </select>
          <LocationPickerMap label={pointName} initialPoint={personalPoints[pointName]} onSave={savePoint} saveText={`Salvează ${pointName}`} />
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {Object.entries(personalPoints).filter(([, coords]) => coords).map(([name, coords]) => (
            <PersonalPointCard key={name} name={name} coords={coords} stations={stations} />
          ))}
        </div>
      </section>
    </div>
  );
}

function PersonalPointCard({ name, coords, stations }) {
  const nearestBike = nearest(stations.filter((s) => s.is_online && s.bikes_available > 0), coords);
  const nearestReturn = nearest(stations.filter((s) => s.is_online && s.empty_doors > 0), coords);
  const worth = nearestBike && nearestReturn && nearestBike.distance < 800 && nearestReturn.distance < 800;

  return (
    <div className="rounded-3xl border border-white/10 bg-app-card p-4">
      <h4 className="font-black text-white">{name}</h4>
      <p className="text-xs text-slate-500">{coords.lat.toFixed(5)}, {coords.lon.toFixed(5)}</p>
      <p className={`mt-2 text-sm font-bold ${worth ? "text-app-green" : "text-app-orange"}`}>{worth ? "Merită VeloTM aici" : "Nu merită mereu aici"}</p>
      <div className="mt-3 grid gap-3">
        {nearestBike ? <MiniStation label="Preluare" item={nearestBike} /> : <span className="text-sm text-slate-400">Fără stație de preluare.</span>}
        {nearestReturn ? <MiniStation label="Returnare" item={nearestReturn} /> : <span className="text-sm text-slate-400">Fără stație de returnare.</span>}
      </div>
    </div>
  );
}

function nearest(stations, coords) {
  const sorted = stations.map((station) => ({
    ...station,
    distance: haversineDistance(coords.lat, coords.lon, station.latitude, station.longitude)
  })).sort((a, b) => a.distance - b.distance);
  return sorted[0];
}

function MiniStation({ label, item }) {
  return (
    <div className="rounded-2xl bg-white/5 p-3 text-sm">
      <span className="text-slate-400">{label}</span>
      <p className="font-bold text-white">{item.name}</p>
      <p className="text-slate-400">{formatDistance(item.distance)} · 🚲 {item.bikes_available} · 🔓 {item.empty_doors}</p>
    </div>
  );
}
