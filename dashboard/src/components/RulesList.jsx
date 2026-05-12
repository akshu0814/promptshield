import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
const SEVERITY_ORDER = { critical: 0, high: 1, medium: 2, low: 3 };
const CATEGORIES = ["prompt_injection", "jailbreak", "extraction", "pii_exfiltration"];
const SEVERITIES = ["low", "medium", "high", "critical"];

const EMPTY_FORM = { name: "", category: "prompt_injection", severity: "high", pattern: "", description: "" };

export default function RulesList() {
  const [rules, setRules] = useState([]);
  const [filter, setFilter] = useState("all");
  const [form, setForm] = useState(EMPTY_FORM);
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");

  const loadRules = () =>
    fetch(`${API}/rules`)
      .then((r) => r.json())
      .then((data) =>
        setRules(data.sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]))
      )
      .catch(() => {});

  useEffect(() => { loadRules(); }, []);

  const categories = ["all", ...new Set(rules.map((r) => r.category))];
  const filtered = filter === "all" ? rules : rules.filter((r) => r.category === filter);

  const handleCreate = async (e) => {
    e.preventDefault();
    setError("");
    setCreating(true);
    try {
      const res = await fetch(`${API}/rules`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (res.ok) {
        setForm(EMPTY_FORM);
        setShowForm(false);
        loadRules();
      } else {
        const data = await res.json();
        setError(data.detail || "Failed to create rule");
      }
    } finally {
      setCreating(false);
    }
  };

  const handleToggle = async (rule) => {
    await fetch(`${API}/rules/${rule.rule_id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: !rule.enabled }),
    });
    loadRules();
  };

  const handleDelete = async (ruleId) => {
    if (!confirm("Delete this custom rule?")) return;
    await fetch(`${API}/rules/${ruleId}`, { method: "DELETE" });
    loadRules();
  };

  return (
    <div className="rules-container">
      <div className="rules-header">
        <h2>Detection Rules ({rules.length})</h2>
        <div className="rules-header-actions">
          <div className="rules-filters">
            {categories.map((cat) => (
              <button
                key={cat}
                className={`filter-btn ${filter === cat ? "active" : ""}`}
                onClick={() => setFilter(cat)}
              >
                {cat}
              </button>
            ))}
          </div>
          <button className="btn-primary" onClick={() => { setShowForm(!showForm); setError(""); }}>
            {showForm ? "Cancel" : "+ Add Rule"}
          </button>
        </div>
      </div>

      {showForm && (
        <form className="rule-create-form" onSubmit={handleCreate}>
          <div className="rule-form-row">
            <input
              className="app-input"
              placeholder="Rule name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
            <select
              className="app-input"
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
            >
              {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <select
              className="app-input"
              value={form.severity}
              onChange={(e) => setForm({ ...form, severity: e.target.value })}
            >
              {SEVERITIES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div className="rule-form-row">
            <input
              className="app-input"
              placeholder="Regex pattern (e.g. ignore.{0,20}instructions)"
              value={form.pattern}
              onChange={(e) => setForm({ ...form, pattern: e.target.value })}
              required
              style={{ flex: 2 }}
            />
            <input
              className="app-input"
              placeholder="Description (optional)"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
          {error && <div className="rule-form-error">{error}</div>}
          <button className="btn-primary" type="submit" disabled={creating}>
            {creating ? "Creating…" : "Create Rule"}
          </button>
        </form>
      )}

      <div className="rules-list">
        {filtered.map((rule) => (
          <div key={rule.rule_id} className={`rule-item ${!rule.enabled ? "rule-disabled" : ""}`}>
            <div className="rule-top">
              <span className="rule-id">{rule.rule_id}</span>
              <span className={`badge badge-${rule.severity}`}>{rule.severity.toUpperCase()}</span>
              <span className="rule-category">{rule.category}</span>
              {rule.source === "custom" && <span className="rule-source-badge">Custom</span>}
              <div className="rule-actions">
                {rule.source === "custom" && (
                  <>
                    <button
                      className={`btn-toggle ${rule.enabled ? "toggle-on" : "toggle-off"}`}
                      onClick={() => handleToggle(rule)}
                      title={rule.enabled ? "Disable" : "Enable"}
                    >
                      {rule.enabled ? "Enabled" : "Disabled"}
                    </button>
                    <button className="btn-danger-sm" onClick={() => handleDelete(rule.rule_id)}>
                      Delete
                    </button>
                  </>
                )}
              </div>
            </div>
            <div className="rule-name">{rule.name}</div>
            {rule.description && <div className="rule-description">{rule.description}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}
