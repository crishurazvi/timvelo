import { AlertTriangle } from "lucide-react";

export default function ErrorState({ title = "A apărut o problemă", message, onRetry }) {
  return (
    <div className="rounded-3xl border border-app-red/30 bg-app-red/10 p-5 text-slate-100">
      <div className="flex items-center gap-3">
        <AlertTriangle className="text-app-red" />
        <div>
          <h3 className="font-bold">{title}</h3>
          <p className="text-sm text-slate-300">{message || "Încearcă din nou în câteva secunde."}</p>
        </div>
      </div>
      {onRetry ? (
        <button onClick={onRetry} className="mt-4 rounded-xl bg-app-cyan px-4 py-2 text-sm font-bold text-slate-950">
          Reîncearcă
        </button>
      ) : null}
    </div>
  );
}
