import { Activity, BarChart3, LogOut, Menu, ShieldCheck, Table2, X } from "lucide-react";
import { useState } from "react";
import { useAuth } from "../auth/AuthContext.jsx";

const tabs = [
  { id: "analyze", label: "Analyze", icon: Activity },
  { id: "dashboard", label: "Dashboard", icon: Table2 },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
];

export function Shell({ activeTab, setActiveTab, children }) {
  const [open, setOpen] = useState(false);
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="brand-row">
          <div className="brand-mark">
            <ShieldCheck size={22} />
          </div>
          <div>
            <strong>FraudShield</strong>
            <span>Risk console</span>
          </div>
        </div>

        <nav className="nav-list">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                className={activeTab === tab.id ? "active" : ""}
                onClick={() => {
                  setActiveTab(tab.id);
                  setOpen(false);
                }}
              >
                <Icon size={18} />
                {tab.label}
              </button>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="user-chip">
            <span>{user?.email?.slice(0, 1).toUpperCase()}</span>
            <p>{user?.email}</p>
          </div>
          <button className="ghost-btn" onClick={logout}>
            <LogOut size={17} />
            Sign out
          </button>
        </div>
      </aside>

      <header className="mobile-topbar">
        <button className="icon-btn" onClick={() => setOpen((value) => !value)} aria-label="Toggle menu">
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
        <strong>FraudShield</strong>
        <button className="topbar-logout" onClick={logout} aria-label="Sign out">
          <LogOut size={17} />
          Logout
        </button>
      </header>

      <nav className="mobile-tabs" aria-label="Primary navigation">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              className={activeTab === tab.id ? "active" : ""}
              onClick={() => {
                setActiveTab(tab.id);
                setOpen(false);
              }}
            >
              <Icon size={17} />
              {tab.label}
            </button>
          );
        })}
      </nav>

      <main className="content">{children}</main>
    </div>
  );
}
