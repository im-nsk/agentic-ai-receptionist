/**
 * AppLayout.jsx
 *
 * - Wraps all protected pages
 * - Injects Navbar
 * - Ensures consistent layout
 */

import Navbar from "../components/Navbar";

export default function AppLayout({ children }) {
  return (
    <div>
      <Navbar />

      <div style={styles.content}>
        {children || <div>Loading...</div>}
      </div>
    </div>
  );
}

const styles = {
  content: {
    padding: "20px 40px",
  },
};