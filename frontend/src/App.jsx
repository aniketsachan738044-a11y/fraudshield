import { useState } from "react";
import { useAuth } from "./auth/AuthContext.jsx";
import { ErrorBoundary } from "./components/ErrorBoundary.jsx";
import { Shell } from "./components/Shell.jsx";
import { Analytics } from "./pages/Analytics.jsx";
import { Analyze } from "./pages/Analyze.jsx";
import { AuthPage } from "./pages/AuthPage.jsx";
import { Dashboard } from "./pages/Dashboard.jsx";
import { RuleStudio } from "./pages/RuleStudio.jsx";

export default function App() {
  const [activeTab, setActiveTab] = useState("analyze");
  const { authenticated, booting } = useAuth();

  if (booting) {
    return (
      <main className="center-screen">
        <div className="loader" />
      </main>
    );
  }

  if (!authenticated) {
    return (
      <ErrorBoundary>
        <AuthPage />
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary>
      <Shell activeTab={activeTab} setActiveTab={setActiveTab}>
        {activeTab === "analyze" && <Analyze />}
        {activeTab === "dashboard" && <Dashboard />}
        {activeTab === "analytics" && <Analytics />}
        {activeTab === "rules" && <RuleStudio />}
      </Shell>
    </ErrorBoundary>
  );
}

