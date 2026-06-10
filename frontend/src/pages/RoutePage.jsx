import RoutePlanner from "../components/RoutePlanner";

export default function RoutePage({ userPosition, personalPoints }) {
  return (
    <div className="space-y-4">
      <div className="rounded-3xl bg-app-card p-5">
        <h2 className="text-2xl font-black">Planificator A → B</h2>
        <p className="mt-1 text-sm text-slate-400">Alegi plecare și destinație, iar backend-ul caută stația optimă de preluare și de returnare.</p>
      </div>
      <RoutePlanner userPosition={userPosition} personalPoints={personalPoints} />
    </div>
  );
}
