export default function MetricCard({ label, value, hint }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-app-card p-4 shadow-glow">
      <div className="text-2xl font-black text-app-cyan">{value ?? "N/A"}</div>
      <div className="mt-1 text-sm text-slate-300">{label}</div>
      {hint ? <div className="mt-1 text-xs text-slate-500">{hint}</div> : null}
    </div>
  );
}
