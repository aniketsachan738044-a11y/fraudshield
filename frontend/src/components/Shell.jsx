import { Activity, BarChart3, Code2, LogOut, Menu, Moon, Network, ShieldCheck, SlidersHorizontal, Sun, Table2, X, Zap } from "lucide-react";
import { useState } from "react";
import { useAuth } from "../auth/AuthContext.jsx";
import { useTheme } from "../context/ThemeContext.jsx";

const tabs = [
  { id: "analyze", label: "Analyze", icon: Activity },
  { id: "dashboard", label: "Dashboard", icon: Table2 },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
  { id: "network", label: "Network Graph", icon: Network },
  { id: "rules", label: "Rule Studio", icon: SlidersHorizontal },
  { id: "developer", label: "Developer API", icon: Code2 },
];


export function Shell({ activeTab, setActiveTab, children }) {
  const [open, setOpen] = useState(false);
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();

  const cycleTheme = () => {
    if (theme === "dark") setTheme("light");
    else if (theme === "light") setTheme("custom");
    else setTheme("dark");
  };

  const themeLabel = theme === "light" ? "Light" : theme === "dark" ? "Dark" : "Custom";

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
          <div className="footer-actions">
            <button
              type="button"
              className="ghost-btn theme-mode-btn"
              onClick={cycleTheme}
              title={`Theme: ${themeLabel} (Click to switch Light / Dark / Custom)`}
            >
              {theme === "light" && <Sun size={15} />}
              {theme === "dark" && <Moon size={15} />}
              {theme === "custom" && <Zap size={15} />}
              <span>{themeLabel}</span>
            </button>
            <button type="button" className="ghost-btn logout-btn" onClick={logout}>
              <LogOut size={15} />
              Sign out
            </button>
          </div>
        </div>
      </aside>

      <header className="mobile-topbar">
        <button className="icon-btn" onClick={() => setOpen((value) => !value)} aria-label="Toggle menu">
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
        <strong>FraudShield</strong>
        <div className="mobile-topbar-right">
          <button
            type="button"
            className="icon-btn theme-mobile-btn"
            onClick={cycleTheme}
            title={`Switch theme (Current: ${themeLabel})`}
            aria-label="Switch theme"
          >
            {theme === "light" && <Sun size={18} />}
            {theme === "dark" && <Moon size={18} />}
            {theme === "custom" && <Zap size={18} />}
          </button>
          <button className="topbar-logout" onClick={logout} aria-label="Sign out">
            <LogOut size={17} />
            Logout
          </button>
        </div>
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
