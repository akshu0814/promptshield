import { useEffect, useRef, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
const WS = API.replace("http", "ws");

const SEVERITY_COLOR = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#22c55e",
};

const SEVERITY_BADGE = {
  critical: "badge-critical",
  high: "badge-high",
  medium: "badge-medium",
  low: "badge-low",
};

function timeAgo(isoString) {
  if (!isoString) return "just now";
  const diff = Math.floor((Date.now() - new Date(isoString)) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

export default function AttackFeed() {
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);

  // Load recent history on mount
  useEffect(() => {
    fetch(`${API}/events?verdict=BLOCK&limit=20`)
      .then((r) => r.json())
      .then((data) => setEvents(data.reverse()))
      .catch(() => {});
  }, []);

  // WebSocket live feed
  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(`${WS}/ws/events`);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        setTimeout(connect, 3000); // reconnect after 3s
      };
      ws.onerror = () => ws.close();

      ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.type === "ping") return;
        setEvents((prev) => [data, ...prev].slice(0, 50)); // keep last 50
      };
    };

    connect();
    return () => wsRef.current?.close();
  }, []);

  return (
    <div className="feed-container">
      <div className="feed-header">
        <h2>Live Attack Feed</h2>
        <span className={`ws-status ${connected ? "ws-connected" : "ws-disconnected"}`}>
          {connected ? "● Live" : "○ Connecting..."}
        </span>
      </div>

      {events.length === 0 ? (
        <div className="feed-empty">
          No attacks detected yet. Try sending a malicious prompt to <code>POST /scan</code>.
        </div>
      ) : (
        <div className="feed-list">
          {events.map((event, i) => (
            <div key={event.event_id || event.id || i} className="feed-item">
              <div className="feed-item-top">
                <span className={`badge ${SEVERITY_BADGE[event.severity] || "badge-low"}`}>
                  {event.severity?.toUpperCase() || "UNKNOWN"}
                </span>
                <span className="feed-category">{event.category || "unknown"}</span>
                <span className="feed-rule">
                  {event.matched_rule?.name || event.matched_rule || "ML Detection"}
                </span>
                <span className="feed-time">{timeAgo(event.created_at)}</span>
              </div>
              <div className="feed-prompt">
                {event.prompt?.slice(0, 120)}
                {event.prompt?.length > 120 ? "…" : ""}
              </div>
              <div className="feed-meta">
                <span>ID: {(event.event_id || event.id || "").slice(0, 8)}...</span>
                <span>{event.scan_duration_ms?.toFixed(2)}ms</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
