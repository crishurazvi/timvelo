import { useCallback, useEffect, useState } from "react";
import { getStations, refreshStations } from "../api/client";

export function useStations(position) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await getStations(position || {});
      setData(payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [position?.lat, position?.lon]);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    try {
      const payload = await refreshStations();
      setData(payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { data, loading, refreshing, error, reload: load, refresh };
}
