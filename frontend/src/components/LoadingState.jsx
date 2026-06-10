export default function LoadingState({ message = "Se încarcă datele VeloTM..." }) {
  return (
    <div className="flex min-h-[320px] flex-col items-center justify-center rounded-3xl border border-white/10 bg-app-card p-8 text-center">
      <div className="h-12 w-12 animate-spin rounded-full border-4 border-app-cyan/20 border-t-app-cyan" />
      <p className="mt-4 text-slate-200">{message}</p>
    </div>
  );
}
