import { RefreshCw, WifiOff } from "lucide-react";
import BottomNav from "./BottomNav";
import { formatDateTime } from "../utils/format";

export default function Layout({ children, activeTab, setActiveTab, updatedAt, warning, onRefresh, refreshing }) {
  return (
    <div className="min-h-screen bg-app-bg pb-24 text-white">
      <header className="sticky top-0 z-[900] border-b border-white/10 bg-app-bg/90 px-4 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black tracking-tight text-white">🚲 VeloTM Radar</h1>
            <p className="text-xs text-slate-400">Actualizat: {formatDateTime(updatedAt)}</p>
          </div>
          <button onClick={onRefresh} disabled={refreshing} className="rounded-2xl bg-app-cyan px-4 py-2 text-sm font-black text-slate-950 disabled:opacity-50">
            <span className="inline-flex items-center gap-2"><RefreshCw size={16} className={refreshing ? "animate-spin" : ""} /> Refresh</span>
          </button>
        </div>
        {warning ? (
          <div className="mx-auto mt-3 flex max-w-5xl items-center gap-2 rounded-2xl border border-app-orange/30 bg-app-orange/10 px-3 py-2 text-xs text-orange-100">
            <WifiOff size={15} /> {warning}
          </div>
        ) : null}
      </header>
      <main className="mx-auto max-w-5xl px-4 py-5">{children}</main>
      <BottomNav active={activeTab} onChange={setActiveTab} />
    </div>
  );
}
