import type { CSSProperties } from "react";
import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Overview", emoji: "🤖" },
  { to: "/builder", label: "Problem Builder", emoji: "🧩" },
  { to: "/editor", label: "Table Editor", emoji: "🧾" },
  { to: "/solver", label: "Solver Hub", emoji: "⚙️" },
  { to: "/constraints", label: "Constraints", emoji: "📊" },
  { to: "/assets", label: "Assets", emoji: "📁" },
  { to: "/settings", label: "Settings", emoji: "🔧" }
];

const activeStyle: CSSProperties = {
  backgroundColor: "#111827",
  color: "#f9fafb"
};

const Sidebar = () => {
  return (
    <aside
      style={{
        width: "260px",
        backgroundColor: "#1f2937",
        color: "#e5e7eb",
        display: "flex",
        flexDirection: "column",
        padding: "24px",
        gap: "12px"
      }}
    >
      <div style={{ fontSize: "1.25rem", fontWeight: 700 }}>FJSP Assistant</div>
      {links.map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          style={({ isActive }: { isActive: boolean }): CSSProperties => ({
            display: "flex",
            alignItems: "center",
            gap: "10px",
            padding: "10px 12px",
            borderRadius: "8px",
            color: "inherit",
            ...(isActive ? activeStyle : { backgroundColor: "transparent" })
          })}
        >
          <span>{link.emoji}</span>
          <span>{link.label}</span>
        </NavLink>
      ))}
    </aside>
  );
};

export default Sidebar;
