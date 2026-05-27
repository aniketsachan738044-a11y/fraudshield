import { Component } from "react";

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="center-screen">
          <section className="auth-panel">
            <p className="eyebrow">FraudShield</p>
            <h1>Something went wrong</h1>
            <p className="muted">Refresh the page and try again.</p>
            <button className="primary-btn" onClick={() => window.location.reload()}>
              Reload
            </button>
          </section>
        </main>
      );
    }

    return this.props.children;
  }
}

