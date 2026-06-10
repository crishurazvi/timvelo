import { useMemo, useState } from "react";
import Layout from "./components/Layout";
import LoadingState from "./components/LoadingState";
import ErrorState from "./components/ErrorState";
import QuickGuide from "./pages/QuickGuide";
import LiveMap from "./pages/LiveMap";
import RoutePage from "./pages/RoutePage";
import FavoritesPage from "./pages/FavoritesPage";
import HistoryPage from "./pages/HistoryPage";
import StatusPage from "./pages/StatusPage";
import { useGeolocation } from "./hooks/useGeolocation";
import { useLocalStorage } from "./hooks/useLocalStorage";
import { useStations } from "./hooks/useStations";

const DEFAULT_PERSONAL_POINTS = {
  "ACASĂ": null,
  SPITAL: null,
  CENTRU: { lat: 45.75596, lon: 21.22676 },
  "GARĂ": { lat: 45.74614, lon: 21.21505 },
  FACULTATE: null,
  "IULIUS TOWN": { lat: 45.76562, lon: 21.22593 },
  CUSTOM: null
};

export default function App() {
  const [activeTab, setActiveTab] = useState("quick");
  const geo = useGeolocation();
  const [favorites, setFavorites] = useLocalStorage("velotm_favorite_stations", []);
  const [personalPoints, setPersonalPoints] = useLocalStorage("velotm_personal_points", DEFAULT_PERSONAL_POINTS);
  const { data, loading, refreshing, error, reload, refresh } = useStations(geo.position);

  const stations = data?.stations || [];
  const favoriteSet = useMemo(() => new Set(favorites), [favorites]);

  function toggleFavorite(stationName) {
    if (!stationName) return;
    if (favoriteSet.has(stationName)) setFavorites(favorites.filter((name) => name !== stationName));
    else setFavorites([...favorites, stationName]);
  }

  if (loading && !data) {
    return <div className="min-h-screen bg-app-bg p-4 text-white"><LoadingState /></div>;
  }

  if (error && !data) {
    return <div className="min-h-screen bg-app-bg p-4 text-white"><ErrorState message={error} onRetry={reload} /></div>;
  }

  let page = null;
  if (activeTab === "quick") {
    page = <QuickGuide data={data} userPosition={geo.position} geo={geo} favorites={favorites} onToggleFavorite={toggleFavorite} onGoRoute={() => setActiveTab("route")} onGoFavorites={() => setActiveTab("favorites")} />;
  } else if (activeTab === "map") {
    page = <LiveMap stations={stations} userPosition={geo.position} favorites={favorites} onToggleFavorite={toggleFavorite} geo={geo} />;
  } else if (activeTab === "route") {
    page = <RoutePage userPosition={geo.position} personalPoints={personalPoints} />;
  } else if (activeTab === "favorites") {
    page = <FavoritesPage stations={stations} favorites={favorites} onToggleFavorite={toggleFavorite} userPosition={geo.position} personalPoints={personalPoints} setPersonalPoints={setPersonalPoints} />;
  } else if (activeTab === "history") {
    page = <HistoryPage stations={stations} />;
  } else {
    page = <StatusPage data={data} />;
  }

  return (
    <Layout activeTab={activeTab} setActiveTab={setActiveTab} updatedAt={data?.updated_at} warning={data?.warning || error} onRefresh={refresh} refreshing={refreshing}>
      {page}
    </Layout>
  );
}
