import { divIcon } from "leaflet";
import { useState } from "react";
import { MapContainer, Marker, TileLayer, useMapEvents } from "react-leaflet";

const DEFAULT_CENTER = [45.7489, 21.2087];

function ClickHandler({ onPick }) {
  useMapEvents({
    click(event) {
      onPick({ lat: event.latlng.lat, lon: event.latlng.lng });
    }
  });
  return null;
}

const pickedIcon = divIcon({
  className: "picked-div-icon",
  html: `<div class="picked-marker"></div>`,
  iconSize: [28, 28],
  iconAnchor: [14, 14]
});

export default function LocationPickerMap({ label = "punct", initialPoint, onSave, saveText }) {
  const [picked, setPicked] = useState(initialPoint || null);
  const center = picked ? [picked.lat, picked.lon] : DEFAULT_CENTER;

  return (
    <div className="rounded-3xl border border-white/10 bg-app-card p-3">
      <p className="mb-3 text-sm text-slate-300">Dă click pe hartă pentru a seta {label}. Nu trebuie să introduci coordonate manual.</p>
      <div className="overflow-hidden rounded-2xl">
        <MapContainer center={center} zoom={14} className="h-[360px] w-full" scrollWheelZoom>
          <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <ClickHandler onPick={setPicked} />
          {picked ? <Marker position={[picked.lat, picked.lon]} icon={pickedIcon} /> : null}
        </MapContainer>
      </div>
      {picked ? (
        <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-slate-400">Lat {picked.lat.toFixed(6)}, Lon {picked.lon.toFixed(6)}</p>
          <button onClick={() => onSave?.(picked)} className="rounded-2xl bg-app-cyan px-4 py-2 text-sm font-black text-slate-950">
            {saveText || `Salvează ${label}`}
          </button>
        </div>
      ) : null}
    </div>
  );
}
