import { Crosshair, MapPinned, Navigation } from "lucide-react";
import MetricCard from "../components/MetricCard";
import StationCard from "../components/StationCard";
import WeatherCard from "../components/WeatherCard";

export default function QuickGuide({ data, userPosition, geo, favorites, onToggleFavorite, onGoRoute, onGoFavorites }) {
  const metrics = data?.metrics || {};
  const nearestBikes = data?.nearest_bike_stations || [];
  const nearestReturns = data?.nearest_return_stations || [];

  return (
    <div className="space-y-5">
      <section className="rounded-3xl border border-white/10 bg-gradient-to-br from-app-card to-app-soft p-5 shadow-glow">
        <p className="text-sm font-bold uppercase tracking-wide text-app-cyan">Mobile-first radar</p>
        <h2 className="mt-2 text-3xl font-black">Unde găsesc rapid o bicicletă?</h2>
        <p className="mt-2 text-slate-300">Permite locația și vezi instant stațiile utile pentru preluare și returnare. Gândită ca o mini aplicație nativă pentru VeloTM.</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-4">
          <button onClick={geo.requestLocation} className="rounded-2xl bg-app-cyan px-4 py-3 font-black text-slate-950"><Crosshair className="mr-2 inline" size={18} /> Permite locația</button>
          <button onClick={onGoRoute} className="rounded-2xl bg-white/10 px-4 py-3 font-bold text-white"><Navigation className="mr-2 inline" size={18} /> Planifică traseu</button>
          <button onClick={onGoFavorites} className="rounded-2xl bg-white/10 px-4 py-3 font-bold text-white"><MapPinned className="mr-2 inline" size={18} /> Setează ACASĂ</button>
          <div className="rounded-2xl bg-white/5 px-4 py-3 text-sm text-slate-300">GPS: <strong>{geo.status}</strong>{geo.error ? <span className="block text-app-orange">{geo.error}</span> : null}</div>
        </div>
      </section>

      <WeatherCard weather={data?.weather} />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <MetricCard label="Biciclete" value={metrics.total_bikes} />
        <MetricCard label="Locuri goale" value={metrics.total_empty_doors} />
        <MetricCard label="Stații online" value={metrics.online_stations} />
        <MetricCard label="Stații offline" value={metrics.offline_stations} />
        <MetricCard label="Fără biciclete" value={metrics.stations_without_bikes} />
      </div>

      {!userPosition ? (
        <div className="rounded-3xl border border-app-orange/30 bg-app-orange/10 p-4 text-sm text-orange-100">
          Nu am primit locația ta. Poți folosi harta și planificatorul cu puncte salvate sau cu selecție manuală pe hartă.
        </div>
      ) : null}

      <section>
        <h2 className="mb-3 text-xl font-black">Cele mai apropiate 3 stații cu biciclete</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {nearestBikes.length ? nearestBikes.map((station) => (
            <StationCard key={station.name} station={station} userPosition={userPosition} onFavorite={onToggleFavorite} isFavorite={favorites.includes(station.name)} />
          )) : <EmptyRecommendation text="Permite locația ca să primesc recomandări lângă tine." />}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-xl font-black">Cele mai apropiate 3 stații pentru returnare</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {nearestReturns.length ? nearestReturns.map((station) => (
            <StationCard key={station.name} station={station} mode="return" userPosition={userPosition} onFavorite={onToggleFavorite} isFavorite={favorites.includes(station.name)} />
          )) : <EmptyRecommendation text="Permite locația ca să văd unde poți lăsa bicicleta." />}
        </div>
      </section>
    </div>
  );
}

function EmptyRecommendation({ text }) {
  return <div className="rounded-3xl bg-app-card p-5 text-sm text-slate-400 md:col-span-3">{text}</div>;
}
