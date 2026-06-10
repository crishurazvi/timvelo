import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts";
import { formatDateTime } from "../utils/format";

export default function HistoryChart({ data = [] }) {
  if (!data.length) {
    return <div className="rounded-3xl bg-app-card p-5 text-sm text-slate-400">Nu există suficient istoric pentru această stație.</div>;
  }

  const chartData = data.map((row) => ({
    ...row,
    label: formatDateTime(row.timestamp)
  }));

  return (
    <div className="rounded-3xl border border-white/10 bg-app-card p-4">
      <div className="h-80 w-full">
        <ResponsiveContainer>
          <LineChart data={chartData} margin={{ top: 10, right: 20, left: -20, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" tick={{ fontSize: 10 }} minTickGap={24} />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Line type="monotone" dataKey="bikes_available" name="Biciclete" strokeWidth={3} dot={false} />
            <Line type="monotone" dataKey="empty_doors" name="Locuri goale" strokeWidth={3} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
