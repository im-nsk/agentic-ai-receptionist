import { useEffect, useState } from "react";
import { getClient } from "../api/client";

export default function Billing() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getClient()
      .then(setData)
      .catch((err) => {
        console.error(err);
        setError("Failed to load billing data");
      });
  }, []);

  if (error) return <div>{error}</div>;
  if (!data) return <div>Loading billing...</div>;

  const usagePercent =
    data.plan_limit > 0
      ? (data.minutes_used / data.plan_limit) * 100
      : 0;

  return (
    <div style={styles.container}>
      <h2>Billing & Usage</h2>

      <div style={styles.card}>
        <p><b>Plan:</b> Free</p>
        <p>
          <b>Usage:</b> {data.minutes_used} / {data.plan_limit} minutes
        </p>

        <div style={styles.progress}>
          <div
            style={{
              ...styles.bar,
              width: `${Math.min(usagePercent, 100)}%`, // ✅ prevent overflow
              background: usagePercent > 80 ? "#ff4d4f" : "#1677ff"
            }}
          />
        </div>

        {usagePercent > 80 && (
          <p style={{ color: "red" }}>
            ⚠️ You’re close to your limit
          </p>
        )}

        <button style={styles.upgrade}>
          Upgrade Plan 🚀
        </button>
      </div>
    </div>
  );
}

const styles = {
  container: { padding: 20 },
  card: {
    border: "1px solid #ddd",
    padding: 20,
    borderRadius: 10,
    maxWidth: 400,
  },
  progress: {
    height: 10,
    background: "#eee",
    marginTop: 10,
    borderRadius: 5,
  },
  bar: {
    height: "100%",
    borderRadius: 5,
  },
  upgrade: {
    marginTop: 20,
    padding: 10,
    background: "#1677ff",
    color: "#fff",
    border: "none",
    borderRadius: 6,
    cursor: "pointer",
  },
};