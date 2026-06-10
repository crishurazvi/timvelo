import { Bike, MapPin, Navigation, Star } from "lucide-react";
import { makeSearchUrl, makeWalkingUrl } from "../utils/googleMaps";

export default function StationCard({ station, mode = "pickup", userPosition, onFavorite, isFavorite }) {
  const color = station.marker_color === "green" ? "border-app-green" : station.marker_color === "orange" ? "border-app-orange" : station.marker_color === "red" ? "border-app-red" : "border-slate-500";
  const destination = { lat: station.latitude, lon: station.longitude };
  const score = mode === "return" ? station.return_score : station.pickup_score;

  return (
    <div className={`rounded-3xl border ${color} bg-app-card p-4 shadow-glow`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-black text-white">{station.name}</h3>
          <p className="mt-1 flex items-center gap-1 text-sm text-slate-400"><MapPin size={14} /> {station.address}</p>
        </div>
        {onFavorite ? (
          <button onClick={() => onFavorite(station.name)} className="rounded-full bg-white/10 p-2 text-slate-200">
            <Star size={18} className={isFavorite ? "fill-app-cyan text-app-cyan" : ""} />
          </button>
        ) : null}
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2 text-center">
        <div className="rounded-2xl bg-white/5 p-3">
          <div className="text-xl font-black text-app-green">{station.bikes_available}</div>
          <div className="text-xs text-slate-400">biciclete</div>
        </div>
        <div className="rounded-2xl bg-white/5 p-3">
          <div className="text-xl font-black text-app-cyan">{station.empty_doors}</div>
          <div className="text-xs text-slate-400">locuri</div>
        </div>
        <div className="rounded-2xl bg-white/5 p-3">
          <div className="text-sm font-black text-white">{station.status}</div>
          <div className="text-xs text-slate-400">status</div>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm text-slate-300">
        <span className="inline-flex items-center gap-1"><Bike size={15} /> {score}</span>
        {station.distance_label ? <span>{station.distance_label}</span> : null}
      </div>
      <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
        <a className="rounded-2xl bg-app-cyan px-4 py-2 text-center text-sm font-bold text-slate-950" href={userPosition ? makeWalkingUrl(userPosition, destination) : makeSearchUrl(destination)} target="_blank" rel="noreferrer">
          <span className="inline-flex items-center gap-2"><Navigation size={15} /> Traseu pe jos</span>
        </a>
        <a className="rounded-2xl bg-white/10 px-4 py-2 text-center text-sm font-bold text-white" href={makeSearchUrl(destination)} target="_blank" rel="noreferrer">
          Google Maps
        </a>
      </div>
    </div>
  );
}
