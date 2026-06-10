import StationMap from "../components/StationMap";

export default function LiveMap({ stations, userPosition, favorites, onToggleFavorite, geo }) {
  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 rounded-3xl bg-app-card p-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-black">Hartă live VeloTM</h2>
          <p className="text-sm text-slate-400">Markerii arată numărul de biciclete disponibile. Verde bun, portocaliu risc, roșu inutil.</p>
        </div>
        <button onClick={geo.requestLocation} className="rounded-2xl bg-app-cyan px-4 py-2 font-black text-slate-950">Centrează pe mine</button>
      </div>
      <StationMap stations={stations} userPosition={userPosition} favorites={favorites} onToggleFavorite={onToggleFavorite} />
    </div>
  );
}
