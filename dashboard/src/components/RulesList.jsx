import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const SEVERITY_ORDER = { critical: 0, high: 1, medium: 2, low: 3 };

export default function RulesList() {
  const [rules, setRules] = useState([]);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    fetch(`${API}/rules`)
      .then((r) => r.json())
      .then((data) =>
        setRules(data.sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]))
      )
      .catch(() => {});
  }, []);

  const categories = ["all", ...new Set(rules.map((r) => r.category))];
  const filtered = filter === "all" ? rules : rules.filter((r) => r.category === filter);

  return (
    <div className="rules-container">
      <div className="rules-header">
        <h2>Detection Rules ({rules.length})</h2>
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
      </div>

      <div className="rules-list">
        {filtered.map((rule) => (
          <div key={rule.rule_id} className="rule-item">
            <div className="rule-top">
              <span className="rule-id">{rule.rule_id}</span>
              <span className={`badge badge-${rule.severity}`}>
                {rule.severity.toUpperCase()}
              </span>
              <span className="rule-category">{rule.category}</span>
            </div>
            <div className="rule-name">{rule.name}</div>
            {rule.description && (
              <div className="rule-description">{rule.description}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
