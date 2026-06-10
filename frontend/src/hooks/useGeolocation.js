import { useCallback, useRef, useState } from "react";

export function useGeolocation() {
  const [status, setStatus] = useState("idle");
  const [position, setPosition] = useState(null);
  const [error, setError] = useState(null);
  const watchId = useRef(null);

  const onSuccess = useCallback((pos) => {
    const coords = {
      lat: pos.coords.latitude,
      lon: pos.coords.longitude,
      accuracy: pos.coords.accuracy
    };
    setPosition(coords);
    setStatus("granted");
    setError(null);
  }, []);

  const onError = useCallback((err) => {
    setStatus(err.code === err.PERMISSION_DENIED ? "denied" : "unavailable");
    setError(err.message || "Nu am putut obține locația.");
  }, []);

  const requestLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setStatus("unavailable");
      setError("Browserul nu suportă geolocație.");
      return;
    }
    setStatus("requesting");
    navigator.geolocation.getCurrentPosition(onSuccess, onError, {
      enableHighAccuracy: true,
      timeout: 12000,
      maximumAge: 60000
    });
  }, [onError, onSuccess]);

  const watchLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setStatus("unavailable");
      return;
    }
    setStatus("requesting");
    watchId.current = navigator.geolocation.watchPosition(onSuccess, onError, {
      enableHighAccuracy: true,
      timeout: 12000,
      maximumAge: 30000
    });
  }, [onError, onSuccess]);

  const clearLocation = useCallback(() => {
    if (watchId.current !== null && navigator.geolocation) {
      navigator.geolocation.clearWatch(watchId.current);
    }
    watchId.current = null;
    setPosition(null);
    setStatus("idle");
    setError(null);
  }, []);

  return { status, position, error, requestLocation, watchLocation, clearLocation };
}
