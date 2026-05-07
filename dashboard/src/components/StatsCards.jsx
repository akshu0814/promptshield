import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function StatsCards() {
  const [stats, setStats] = useState(null);

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API}/stats`);
      const data = await res.json();
      setStats(data);
    } catch {
      // silently fail — API may not be ready
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!stats) {
    return (
      <div className="stats-grid">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="card skeleton" />
        ))}
      </div>
    );
  }

  const cards = [
    {
      label: "Total Scans",
      value: stats.total_scans.toLocaleString(),
      color: "blue",
    },
    {
      label: "Blocked",
      value: stats.blocked.toLocaleString(),
      color: "red",
    },
    {
      label: "Allowed",
      value: stats.allowed.toLocaleString(),
      color: "green",
    },
    {
      label: "Block Rate",
      value: `${(stats.block_rate * 100).toFixed(1)}%`,
      color: "orange",
    },
  ];

  return (
    <div className="stats-grid">
      {cards.map((c) => (
        <div key={c.label} className={`card card-${c.color}`}>
          <div className="card-value">{c.value}</div>
          <div className="card-label">{c.label}</div>
        </div>
      ))}
    </div>
  );
}
