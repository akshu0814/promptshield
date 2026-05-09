import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from "recharts";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const CATEGORY_COLORS = {
  prompt_injection: "#3b82f6",
  jailbreak: "#f97316",
  extraction: "#a855f7",
  pii_exfiltration: "#ec4899",
};

const SEVERITY_COLORS = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#22c55e",
};

function BreakdownBar({ title, data, colorMap, defaultColor }) {
  if (!data || data.length === 0) {
    return (
      <div className="breakdown-half">
        <div className="breakdown-title">{title}</div>
        <div className="chart-empty">No blocked events yet</div>
      </div>
    );
  }

  return (
    <div className="breakdown-half">
      <div className="breakdown-title">{title}</div>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3a" vertical={false} />
          <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} />
          <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} axisLine={false} allowDecimals={false} />
          <Tooltip
            contentStyle={{ background: "#1a1d27", border: "1px solid #2a2d3a", borderRadius: 8 }}
            labelStyle={{ color: "#e2e8f0" }}
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {data.map((entry) => (
              <Cell
                key={entry.name}
                fill={colorMap[entry.name] || defaultColor}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function BreakdownChart() {
  const [breakdown, setBreakdown] = useState(null);

  useEffect(() => {
    const load = () =>
      fetch(`${API}/stats/breakdown`)
        .then((r) => r.json())
        .then(setBreakdown)
        .catch(() => {});

    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  const categoryData = breakdown
    ? Object.entries(breakdown.by_category).map(([name, count]) => ({ name, count }))
    : [];

  const severityData = breakdown
    ? ["critical", "high", "medium", "low"]
        .filter((s) => breakdown.by_severity[s])
        .map((s) => ({ name: s, count: breakdown.by_severity[s] }))
    : [];

  return (
    <div className="chart-container">
      <div className="chart-header">
        <h2>Attack Breakdown</h2>
        {breakdown && (
          <span className="chart-subtitle">
            {breakdown.total_blocked.toLocaleString()} total blocked
          </span>
        )}
      </div>
      <div className="breakdown-grid">
        <BreakdownBar
          title="By Category"
          data={categoryData}
          colorMap={CATEGORY_COLORS}
          defaultColor="#3b82f6"
        />
        <BreakdownBar
          title="By Severity"
          data={severityData}
          colorMap={SEVERITY_COLORS}
          defaultColor="#94a3b8"
        />
      </div>
    </div>
  );
}
