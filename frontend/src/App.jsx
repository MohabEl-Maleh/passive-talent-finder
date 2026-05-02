// frontend/src/App.jsx
// Root component. Handles role selection (Recruiter / Hiring Manager)
// and sets up all page routing.
// To add a new HR module later, just add a new <Route> here.

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { RoleProvider, useRole } from "./context/RoleContext";

// Pages
import RoleSelector   from "./pages/RoleSelector";
import JobSetup       from "./pages/JobSetup";
import UploadCVs      from "./pages/UploadCVs";
import Results        from "./pages/Results";
import ShortlistPage  from "./pages/ShortlistPage";
import HMDashboard    from "./pages/HMDashboard";

// Shared layout
import Layout from "./components/shared/Layout";

function AppRoutes() {
  const { role } = useRole();

  if (!role) return <RoleSelector />;

  return (
    <Layout>
      <Routes>
        {/* ── Recruiter flow ───────────────────────────── */}
        <Route path="/"              element={<Navigate to="/job-setup" />} />
        <Route path="/job-setup"     element={<JobSetup />} />
        <Route path="/upload/:jobId" element={<UploadCVs />} />
        <Route path="/results/:jobId" element={<Results />} />
        <Route path="/shortlist/:jobId" element={<ShortlistPage />} />

        {/* ── Hiring Manager flow ──────────────────────── */}
        <Route path="/hm-dashboard"       element={<HMDashboard />} />
        <Route path="/hm-review/:jobId"   element={<ShortlistPage />} />

        {/* ── Future HR modules go here ────────────────── */}
        {/* <Route path="/onboarding" element={<Onboarding />} /> */}
      </Routes>
    </Layout>
  );
}

export default function App() {
  return (
    <RoleProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </RoleProvider>
  );
}
