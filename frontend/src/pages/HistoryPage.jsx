import { useEffect, useMemo, useState } from "react";
import { getEvents, getHistory } from "../api/client";
import EventList from "../components/EventList";
import HistoryChart from "../components/HistoryChart";
import ErrorState from "../components/ErrorState";

export default function HistoryPage({ stations }) {
  const [selected, setSelected] = useState(stations?.[0]?.name || "");
  const [history, setHistory] = useState([]);
  const [events, setEvents] = useState([]);
  const [error, setError] = useState(null);
  const stationNames = useMemo(() => stations.map((s) => s.name).sort(), [stations]);

  useEffect(() => {
    if (!selected && stationNames.length) setSelected(stationNames[0]);
  }, [selected, stationNames]);

  useEffect(() => {
    async function load() {
      if (!selected) return;
      setError(null);
      try {
        const [hist, ev] = await Promise.all([getHistory(selected), getEvents()]);
        setHistory(hist);
        setEvents(ev);
      } catch (err) {
        setError(err.message);
      }
    }
    load();
  }, [selected]);

  const interpretation = interpretHistory(history);

  return (
    <div className="space-y-5">
      <section className="rounded-3xl bg-app-card p-5">
        <h2 className="text-2xl font-black">Istoric și evenimente</h2>
        <p className="mt-1 text-sm text-slate-400">SQLite salvează snapshoturi periodice și detectează schimbări utile.</p>
      </section>
      <select value={selected} onChange={(e) => setSelected(e.target.value)} className="w-full rounded-2xl bg-app-card p-3 text-white">
        {stationNames.map((name) => <option key={name} value={name}>{name}</option>)}
      </select>
      {error ? <ErrorState message={error} /> : null}
      <div className="rounded-3xl border border-white/10 bg-app-card p-4 text-sm text-slate-300">
        {interpretation}
      </div>
      <HistoryChart data={history} />
      <section>
        <h3 className="mb-3 text-xl font-black">Evenimente recente</h3>
        <EventList events={events} />
      </section>
    </div>
  );
}

function interpretHistory(history) {
  if (!history || history.length < 4) return "Nu există suficient istoric pentru o interpretare robustă.";
  const avgBikes = history.reduce((sum, row) => sum + Number(row.bikes_available || 0), 0) / history.length;
  const avgDoors = history.reduce((sum, row) => sum + Number(row.empty_doors || 0), 0) / history.length;
  if (avgBikes < 1) return "Stația pare frecvent goală. Nu te baza pe ea pentru preluare.";
  if (avgDoors < 1) return "Stația pare frecvent plină. Atenție pentru returnare.";
  if (avgBikes >= 4) return "Stația are de obicei biciclete disponibile.";
  return "Stația are disponibilitate variabilă. Verificarea live rămâne importantă.";
}
