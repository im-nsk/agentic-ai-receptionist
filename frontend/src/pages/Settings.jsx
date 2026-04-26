import { useState } from "react";

export default function Settings() {
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const handleSave = () => {
    if (loading) return;

    setMessage("");

    if (!name.trim()) {
      setMessage("Please enter a business name");
      return;
    }

    try {
      setLoading(true);

      // 🚀 later: connect API
      alert("Saved (connect backend later)");

      setMessage("✅ Saved successfully");

    } catch (err) {
      console.error(err);
      setMessage("❌ Failed to save");

    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <h2>Settings</h2>

      <div style={styles.card}>
        <input
          placeholder="Business Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          style={styles.input}
        />

        <button
          onClick={handleSave}
          style={styles.button}
          disabled={loading}
        >
          {loading ? "Saving..." : "Save Changes"}
        </button>

        {message && <p style={styles.message}>{message}</p>}
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
  input: {
    width: "100%",
    padding: 10,
    marginBottom: 10,
  },
  button: {
    padding: 10,
    background: "#1677ff",
    color: "#fff",
    border: "none",
    borderRadius: 6,
    cursor: "pointer",
  },
  message: {
    marginTop: 10,
    fontSize: 12,
  },
};