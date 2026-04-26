/**
 * main.jsx (FINAL Production Safe)
 */

import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "./App.jsx";
import "./index.css";

/**
 * 🛡️ Global Error Boundary
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error("App Crash:", error, info);
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={styles.errorContainer}>
          <h2>Something went wrong</h2>
          <p>Please try refreshing the page</p>

          <button onClick={this.handleReload} style={styles.button}>
            Reload App
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * 🔍 Root check
 */
const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Root element not found. Check index.html");
}

/**
 * 🚀 Create root
 */
const root = ReactDOM.createRoot(rootElement);

/**
 * 🌍 Render
 */
root.render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>
);

/**
 * 🎨 Styles
 */
const styles = {
  errorContainer: {
    height: "100vh",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    fontFamily: "sans-serif",
    gap: "10px",
  },
  button: {
    padding: "10px 15px",
    border: "none",
    borderRadius: "6px",
    background: "#1677ff",
    color: "#fff",
    cursor: "pointer",
  },
};