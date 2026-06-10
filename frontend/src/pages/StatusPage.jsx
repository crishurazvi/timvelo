import MetricCard from "../components/MetricCard";
import { stationProblemLabel } from "../utils/stationScore";

export default function StatusPage({ data }) {
  const stations = data?.stations || [];
  const metrics = data?.metrics || {};
  const topBikes = [...stations].sort((a, b) => b.bikes_available - a.bikes_available).slice(0, 5);
  const topReturns = [...stations].sort((a, b) => b.empty_doors - a.empty_doors).slice(0, 5);
  const problematic = stations.filter((s) => stationProblemLabel(s) !== "OK").slice(0, 10);

  return (
    <div className="space-y-5">
      <section className="rounded-3xl bg-app-card p-5">
        <h2 className="text-2xl font-black">Status rețea</h2>
        <p className="mt-1 text-sm text-slate-400">Topuri rapide și stații problematice.</p>
      </section>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        <MetricCard label="Biciclete" value={metrics.total_bikes} />
        <MetricCard label="Locuri goale" value={metrics.total_empty_doors} />
        <MetricCard label="Online" value={metrics.online_stations} />
        <MetricCard label="Offline" value={metrics.offline_stations} />
        <MetricCard label="Fără biciclete" value={metrics.stations_without_bikes} />
        <MetricCard label="Fără locuri" value={metrics.stations_without_empty_doors} />
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <TopList title="Top biciclete" items={topBikes} value={(s) => `🚲 ${s.bikes_available}`} />
        <TopList title="Top locuri goale" items={topReturns} value={(s) => `🔓 ${s.empty_doors}`} />
        <TopList title="Problematice" items={problematic} value={(s) => stationProblemLabel(s)} />
      </div>
    </div>
  );
}

function TopList({ title, items, value }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-app-card p-4">
      <h3 className="font-black">{title}</h3>
      <div className="mt-3 space-y-2">
        {items.map((item) => (
          <div key={item.name} className="flex items-center justify-between gap-3 rounded-2xl bg-white/5 p-3 text-sm">
            <span className="truncate text-slate-200">{item.name}</span>
            <span className="whitespace-nowrap font-bold text-app-cyan">{value(item)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
