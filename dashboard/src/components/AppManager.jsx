import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function AppManager() {
  const [apps, setApps] = useState([]);
  const [name, setName] = useState("");
  const [blockMode, setBlockMode] = useState(true);
  const [creating, setCreating] = useState(false);
  const [copiedKey, setCopiedKey] = useState(null);

  const loadApps = () =>
    fetch(`${API}/apps`)
      .then((r) => r.json())
      .then(setApps)
      .catch(() => {});

  useEffect(() => {
    loadApps();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    try {
      const res = await fetch(`${API}/apps`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), block_mode: blockMode }),
      });
      if (res.ok) {
        setName("");
        loadApps();
      }
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (appId) => {
    if (!confirm("Delete this app?")) return;
    await fetch(`${API}/apps/${appId}`, { method: "DELETE" });
    loadApps();
  };

  const copyKey = (key, appId) => {
    navigator.clipboard.writeText(key);
    setCopiedKey(appId);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  return (
    <div className="apps-container">
      <div className="apps-header">
        <h2>Registered Apps</h2>
        <span className="apps-count">{apps.length} app{apps.length !== 1 ? "s" : ""}</span>
      </div>

      <form className="app-create-form" onSubmit={handleCreate}>
        <input
          className="app-input"
          type="text"
          placeholder="App name (e.g. my-chatbot)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={200}
        />
        <label className="app-toggle">
          <input
            type="checkbox"
            checked={blockMode}
            onChange={(e) => setBlockMode(e.target.checked)}
          />
          <span>Block mode</span>
        </label>
        <button className="btn-primary" type="submit" disabled={creating || !name.trim()}>
          {creating ? "Creating…" : "Register App"}
        </button>
      </form>

      {apps.length === 0 ? (
        <div className="apps-empty">No apps registered yet — create one above</div>
      ) : (
        <div className="apps-list">
          {apps.map((app) => (
            <div key={app.app_id} className="app-item">
              <div className="app-item-top">
                <span className="app-name">{app.name}</span>
                <span className={`app-mode ${app.block_mode ? "mode-block" : "mode-monitor"}`}>
                  {app.block_mode ? "Block" : "Monitor"}
                </span>
                <span className="app-scans">{(app.total_scans || 0).toLocaleString()} scans</span>
                <button className="btn-danger-sm" onClick={() => handleDelete(app.app_id)}>
                  Delete
                </button>
              </div>
              <div className="app-item-key">
                <span className="key-label">API Key</span>
                <code className="key-value">{app.api_key}</code>
                <button
                  className="btn-copy"
                  onClick={() => copyKey(app.api_key, app.app_id)}
                >
                  {copiedKey === app.app_id ? "Copied!" : "Copy"}
                </button>
              </div>
              <div className="app-item-meta">
                App ID: <code>{app.app_id}</code> · Created {new Date(app.created_at).toLocaleDateString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
