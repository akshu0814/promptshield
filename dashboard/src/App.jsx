import { useState } from "react";
import StatsCards from "./components/StatsCards";
import AttackFeed from "./components/AttackFeed";
import RulesList from "./components/RulesList";
import TimeseriesChart from "./components/TimeseriesChart";
import BreakdownChart from "./components/BreakdownChart";
import AppManager from "./components/AppManager";
import "./index.css";

const TABS = ["Live Feed", "Analytics", "Apps", "Rules"];

export default function App() {
  const [tab, setTab] = useState("Live Feed");

  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <div className="logo">
            <span className="logo-icon">🛡️</span>
            <span className="logo-text">PromptShield</span>
            <span className="logo-sub">Defense Dashboard</span>
          </div>
          <nav className="tabs">
            {TABS.map((t) => (
              <button
                key={t}
                className={`tab-btn ${tab === t ? "active" : ""}`}
                onClick={() => setTab(t)}
              >
                {t}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="main">
        <StatsCards />
        {tab === "Live Feed" && <AttackFeed />}
        {tab === "Analytics" && (
          <>
            <TimeseriesChart />
            <BreakdownChart />
          </>
        )}
        {tab === "Apps" && <AppManager />}
        {tab === "Rules" && <RulesList />}
      </main>

      <footer className="footer">
        PromptShield — Open-source LLM prompt injection defense
      </footer>
    </div>
  );
}
