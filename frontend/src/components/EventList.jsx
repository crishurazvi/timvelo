import { Activity } from "lucide-react";
import { formatDateTime } from "../utils/format";

export default function EventList({ events = [] }) {
  if (!events.length) {
    return <div className="rounded-3xl bg-app-card p-5 text-sm text-slate-400">Nu există evenimente recente.</div>;
  }
  return (
    <div className="space-y-3">
      {events.map((event, index) => (
        <div key={`${event.timestamp}-${event.station_name}-${index}`} className="rounded-3xl border border-white/10 bg-app-card p-4">
          <div className="flex gap-3">
            <Activity className="mt-1 text-app-cyan" size={18} />
            <div>
              <p className="font-bold text-white">{event.message}</p>
              <p className="text-xs text-slate-500">{formatDateTime(event.timestamp)} · {event.event_type}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
