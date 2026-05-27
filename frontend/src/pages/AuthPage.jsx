import { ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useAuth } from "../auth/AuthContext.jsx";

export function AuthPage() {
  const [mode, setMode] = useState("register");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register({ email, password, full_name: fullName || null });
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-layout">
      <section className="auth-hero">
        <div className="brand-mark large">
          <ShieldCheck size={34} />
        </div>
        <h1>FraudShield</h1>
        <p>Transaction fraud scoring with explainable alerts and export-ready reports.</p>
      </section>

      <section className="auth-panel">
        <div className="segmented">
          <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")} type="button">
            Login
          </button>
          <button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")} type="button">
            Register
          </button>
        </div>

        <form onSubmit={handleSubmit} className="form-stack">
          {mode === "register" && (
            <label>
              User name
              <input value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Enter your name" />
            </label>
          )}
          <label>
            Email
            <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={8}
              required
            />
          </label>

          {error && <p className="error-text">{error}</p>}

          <button className="primary-btn" disabled={loading}>
            {loading ? "Please wait..." : mode === "login" ? "Login" : "Create account"}
          </button>
        </form>
      </section>
    </main>
  );
}
