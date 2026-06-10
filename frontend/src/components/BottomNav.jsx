import { Bike, Clock3, Heart, Map, Route, Gauge } from "lucide-react";

const items = [
  { id: "quick", label: "Ghid", icon: Bike },
  { id: "map", label: "Hartă", icon: Map },
  { id: "route", label: "Traseu", icon: Route },
  { id: "favorites", label: "Favorite", icon: Heart },
  { id: "history", label: "Istoric", icon: Clock3 },
  { id: "status", label: "Status", icon: Gauge }
];

export default function BottomNav({ active, onChange }) {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-[1000] border-t border-white/10 bg-app-card/95 px-2 py-2 backdrop-blur">
      <div className="mx-auto grid max-w-3xl grid-cols-6 gap-1">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = active === item.id;
          return (
            <button key={item.id} onClick={() => onChange(item.id)} className={`flex flex-col items-center justify-center rounded-2xl px-2 py-2 text-xs ${isActive ? "bg-app-cyan text-slate-950" : "text-slate-400"}`}>
              <Icon size={18} />
              <span className="mt-1">{item.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
