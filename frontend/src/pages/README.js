// frontend/src/pages/RoleSelector.jsx
// First screen the user sees — pick Recruiter or Hiring Manager.
// No login system needed for demo. Role is stored in React context.
export { default } from "../components/shared/RoleSelectorView";

// ─────────────────────────────────────────────────────────────────────────────
// frontend/src/pages/JobSetup.jsx         → REQ-PH-101, 103 (Hiring Manager defines job)
// frontend/src/pages/UploadCVs.jsx        → REQ-PH-102 (upload + fresh/append mode)
// frontend/src/pages/Results.jsx          → REQ-PH-201,202,203,204 | PRED-01,02,05
// frontend/src/pages/ShortlistPage.jsx    → REQ-PH-301-306 | PRED-03,04
// frontend/src/pages/HMDashboard.jsx      → REQ-PH-501 (talent availability dashboard)
//
// These are all stub files — we build each one fully, one at a time.
// Each page imports only from components/recruiter or components/hiring-manager
// so the two roles never share business logic.
