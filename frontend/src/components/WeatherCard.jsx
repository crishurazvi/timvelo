import { CloudSun, Wind, Droplets, Thermometer } from "lucide-react";

export default function WeatherCard({ weather }) {
  if (!weather || weather.weather_available === false) {
    return (
      <div className="rounded-3xl border border-white/10 bg-app-card p-5">
        <div className="flex items-center gap-3 text-slate-200">
          <CloudSun className="text-slate-400" />
          <div>
            <h3 className="font-bold">Meteo bicicletă</h3>
            <p className="text-sm text-slate-400">Datele meteo nu sunt disponibile momentan.</p>
          </div>
        </div>
      </div>
    );
  }

  const scoreClass = weather.score >= 8 ? "text-app-green" : weather.score >= 5 ? "text-app-orange" : "text-app-red";

  return (
    <div className="rounded-3xl border border-white/10 bg-app-card p-5 shadow-glow">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-slate-300">
            <CloudSun size={18} className="text-app-cyan" />
            <span className="text-sm">Meteo bicicletă</span>
          </div>
          <h3 className={`mt-2 text-3xl font-black ${scoreClass}`}>{weather.score}/10</h3>
          <p className="font-bold text-white">{weather.label}</p>
          <p className="mt-1 text-sm text-slate-400">{weather.reason}</p>
        </div>
        <div className="grid gap-2 text-sm text-slate-300">
          <span className="flex items-center gap-2"><Thermometer size={16} /> {weather.temperature}°C</span>
          <span className="flex items-center gap-2"><Wind size={16} /> {weather.wind_speed} km/h</span>
          <span className="flex items-center gap-2"><Droplets size={16} /> {weather.precipitation} mm</span>
        </div>
      </div>
    </div>
  );
}
