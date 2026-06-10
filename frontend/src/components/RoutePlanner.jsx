import { useMemo, useState } from "react";
import { getRoute } from "../api/client";
import LocationPickerMap from "./LocationPickerMap";
import ErrorState from "./ErrorState";

const DEFAULT_POINTS = {
  CENTRU: { lat: 45.75596, lon: 21.22676 },
  GARĂ: { lat: 45.74614, lon: 21.21505 },
  "IULIUS TOWN": { lat: 45.76562, lon: 21.22593 }
};

function optionsFromPoints(points, hasCurrent) {
  const options = [];
  if (hasCurrent) options.push({ id: "current", label: "Poziția mea curentă" });
  Object.entries({ ...DEFAULT_POINTS, ...points }).forEach(([name, coords]) => {
    if (coords) options.push({ id: `point:${name}`, label: name, coords });
  });
  options.push({ id: "map", label: "Selectează pe hartă" });
  options.push({ id: "manual", label: "Coordonate manuale" });
  return options;
}

export default function RoutePlanner({ userPosition, personalPoints }) {
  const [startChoice, setStartChoice] = useState(userPosition ? "current" : "point:CENTRU");
  const [destChoice, setDestChoice] = useState("point:IULIUS TOWN");
  const [startMap, setStartMap] = useState(null);
  const [destMap, setDestMap] = useState(null);
  const [manualStart, setManualStart] = useState({ lat: "", lon: "" });
  const [manualDest, setManualDest] = useState({ lat: "", lon: "" });
  const [route, setRoute] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const options = useMemo(() => optionsFromPoints(personalPoints || {}, Boolean(userPosition)), [personalPoints, userPosition]);

  function resolve(choice, mapPoint, manualPoint) {
    if (choice === "current") return userPosition;
    if (choice === "map") return mapPoint;
    if (choice === "manual") {
      const lat = Number(manualPoint.lat);
      const lon = Number(manualPoint.lon);
      return Number.isFinite(lat) && Number.isFinite(lon) ? { lat, lon } : null;
    }
    if (choice.startsWith("point:")) {
      const name = choice.replace("point:", "");
      return { ...DEFAULT_POINTS, ...(personalPoints || {}) }[name] || null;
    }
    return null;
  }

  async function planRoute() {
    const start = resolve(startChoice, startMap, manualStart);
    const destination = resolve(destChoice, destMap, manualDest);
    if (!start || !destination) {
      setError("Alege punctul A și punctul B înainte de calcul.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setRoute(await getRoute(start, destination));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-3xl bg-app-card p-4">
          <label className="text-sm font-bold text-slate-300">Punct A</label>
          <select value={startChoice} onChange={(e) => setStartChoice(e.target.value)} className="mt-2 w-full rounded-2xl bg-app-soft p-3 text-white">
            {options.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
          </select>
          {startChoice === "map" ? <div className="mt-3"><LocationPickerMap label="punctul A" onSave={setStartMap} saveText="Folosește ca punct A" /></div> : null}
          {startChoice === "manual" ? <ManualInputs value={manualStart} onChange={setManualStart} /> : null}
        </div>
        <div className="rounded-3xl bg-app-card p-4">
          <label className="text-sm font-bold text-slate-300">Punct B</label>
          <select value={destChoice} onChange={(e) => setDestChoice(e.target.value)} className="mt-2 w-full rounded-2xl bg-app-soft p-3 text-white">
            {options.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
          </select>
          {destChoice === "map" ? <div className="mt-3"><LocationPickerMap label="punctul B" onSave={setDestMap} saveText="Folosește ca punct B" /></div> : null}
          {destChoice === "manual" ? <ManualInputs value={manualDest} onChange={setManualDest} /> : null}
        </div>
      </div>

      {error ? <ErrorState message={error} /> : null}
      <button onClick={planRoute} disabled={loading} className="w-full rounded-3xl bg-app-cyan px-5 py-4 font-black text-slate-950 disabled:opacity-60">
        {loading ? "Calculez..." : "Calculează traseul"}
      </button>

      {route ? <RouteResult route={route} /> : null}
    </div>
  );
}

function ManualInputs({ value, onChange }) {
  return (
    <div className="mt-3 grid grid-cols-2 gap-2">
      <input placeholder="lat" value={value.lat} onChange={(e) => onChange({ ...value, lat: e.target.value })} className="rounded-2xl bg-app-soft p-3 text-white" />
      <input placeholder="lon" value={value.lon} onChange={(e) => onChange({ ...value, lon: e.target.value })} className="rounded-2xl bg-app-soft p-3 text-white" />
    </div>
  );
}

function RouteResult({ route }) {
  const verdictClass = route.worth_it ? "border-app-green bg-app-green/10" : "border-app-red bg-app-red/10";
  return (
    <div className={`rounded-3xl border ${verdictClass} p-5`}>
      <h3 className="text-xl font-black">{route.worth_it ? "Merită VeloTM acum" : "Nu merită acum"}</h3>
      <p className="mt-2 text-sm text-slate-300">{route.reason}</p>
      <div className="mt-5 space-y-3 text-sm text-slate-200">
        <p>1. Mergi pe jos până la stația <strong>{route.pickup_station?.name || "indisponibilă"}</strong> {route.walk_to_pickup_label ? `(${route.walk_to_pickup_label})` : ""}.</p>
        <p>2. Ia bicicleta de la stația de preluare.</p>
        <p>3. Pedalează până aproape de destinație {route.bike_distance_label ? `(${route.bike_distance_label})` : ""}.</p>
        <p>4. Lasă bicicleta la stația <strong>{route.return_station?.name || "indisponibilă"}</strong>.</p>
        <p>5. Mergi pe jos până la punctul B {route.walk_from_return_label ? `(${route.walk_from_return_label})` : ""}.</p>
      </div>
      <div className="mt-5 grid gap-2 sm:grid-cols-2">
        {route.pickup_google_maps_url ? <a href={route.pickup_google_maps_url} target="_blank" rel="noreferrer" className="rounded-2xl bg-app-cyan px-4 py-3 text-center font-bold text-slate-950">Traseu către preluare</a> : null}
        {route.return_google_maps_url ? <a href={route.return_google_maps_url} target="_blank" rel="noreferrer" className="rounded-2xl bg-white/10 px-4 py-3 text-center font-bold text-white">Traseu de la returnare</a> : null}
      </div>
    </div>
  );
}
