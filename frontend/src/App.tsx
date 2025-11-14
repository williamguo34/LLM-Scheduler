import type { CSSProperties } from "react";
import { Routes, Route } from "react-router-dom";

import Sidebar from "./components/Sidebar";
import OverviewPage from "./pages/OverviewPage";
import ProblemBuilderPage from "./pages/ProblemBuilderPage";
import TableEditorPage from "./pages/TableEditorPage";
import SolverHubPage from "./pages/SolverHubPage";
import ConstraintsPage from "./pages/ConstraintsPage";
import AssetsPage from "./pages/AssetsPage";
import SettingsPage from "./pages/SettingsPage";

const appShellStyle: CSSProperties = {
  minHeight: "100vh",
  display: "flex",
  backgroundColor: "#0f172a"
};

const mainStyle: CSSProperties = {
  flex: 1,
  padding: "32px",
  backgroundColor: "#f9fafb"
};

const App = () => (
  <div style={appShellStyle}>
    <Sidebar />
    <main style={mainStyle}>
      <Routes>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/builder" element={<ProblemBuilderPage />} />
        <Route path="/editor" element={<TableEditorPage />} />
        <Route path="/solver" element={<SolverHubPage />} />
        <Route path="/constraints" element={<ConstraintsPage />} />
        <Route path="/assets" element={<AssetsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </main>
  </div>
);

export default App;
