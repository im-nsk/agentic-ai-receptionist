export default function Analytics() {
  return (
    <div style={styles.container}>
      <h2>Analytics</h2>

      <div style={styles.card}>
        <p><b>Total Bookings:</b> 24</p>
        <p><b>Today’s Calls:</b> 5</p>
        <p><b>Conversion Rate:</b> 68%</p>
      </div>

      <p style={styles.note}>
        (You’ll connect real data later)
      </p>
    </div>
  );
}

const styles = {
  container: { padding: "40px" },
  card: {
    border: "1px solid #ddd",
    padding: 20,
    borderRadius: 10,
    maxWidth: 400,
  },
  note: {
    marginTop: 10,
    fontSize: 12,
    color: "#888",
  },
};