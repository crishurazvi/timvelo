import StationCard from "./StationCard";

export default function FavoriteStations({ stations = [], favorites = [], userPosition, onToggleFavorite }) {
  const favoriteSet = new Set(favorites);
  const favoriteStations = stations.filter((s) => favoriteSet.has(s.name));

  if (!favoriteStations.length) {
    return <div className="rounded-3xl bg-app-card p-5 text-sm text-slate-400">Nu ai stații favorite încă. Le poți adăuga din hartă sau din cardurile de stații.</div>;
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {favoriteStations.map((station) => (
        <StationCard key={station.name} station={station} userPosition={userPosition} onFavorite={onToggleFavorite} isFavorite />
      ))}
    </div>
  );
}
