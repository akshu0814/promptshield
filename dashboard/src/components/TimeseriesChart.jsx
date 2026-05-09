import { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
const HOUR_OPTIONS = [
  { label: "24h", value: 24 },
  { label: "48h", value: 48 },
  { label: "7d", value: 168 },
];

function formatHour(iso) {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:00`;
}

export default function TimeseriesChart() {
  const [hours, setHours] = useState(24);
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${API}/stats/timeseries?hours=${hours}`)
      .then((r) => r.json())
      .then((res) => {
        setData(
          (res.buckets || []).map((b) => ({
            time: formatHour(b.timestamp),
            total: b.total,
            blocked: b.blocked,
            allowed: b.allowed,
          }))
        );
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [hours]);

  return (
    <div className="chart-container">
      <div className="chart-header">
        <h2>Attacks Over Time</h2>
        <div className="chart-filters">
          {HOUR_OPTIONS.map((o) => (
            <button
              key={o.value}
              className={`filter-btn ${hours === o.value ? "active" : ""}`}
              onClick={() => setHours(o.value)}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="chart-loading" />
      ) : data.length === 0 ? (
        <div className="chart-empty">No data for this window — run some scans first</div>
      ) : (
        <div className="chart-body">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3a" />
              <XAxis dataKey="time" tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} axisLine={false} allowDecimals={false} />
              <Tooltip
                contentStyle={{ background: "#1a1d27", border: "1px solid #2a2d3a", borderRadius: 8 }}
                labelStyle={{ color: "#e2e8f0" }}
              />
              <Legend wrapperStyle={{ fontSize: 12, color: "#94a3b8" }} />
              <Line type="monotone" dataKey="blocked" stroke="#ef4444" strokeWidth={2} dot={false} name="Blocked" />
              <Line type="monotone" dataKey="allowed" stroke="#22c55e" strokeWidth={2} dot={false} name="Allowed" />
              <Line type="monotone" dataKey="total" stroke="#3b82f6" strokeWidth={2} dot={false} name="Total" strokeDasharray="4 2" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
