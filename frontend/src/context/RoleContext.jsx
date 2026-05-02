// frontend/src/context/RoleContext.jsx
// Global role state. Determines which UI features are visible.
// Recruiter sees: upload, run AI, view results, initiate outreach.
// Hiring Manager sees: review shortlist, approve/reject, provide feedback.

import { createContext, useContext, useState } from "react";

const RoleContext = createContext(null);

export function RoleProvider({ children }) {
  const [role, setRole] = useState(null); // "recruiter" | "hiring_manager"
  return (
    <RoleContext.Provider value={{ role, setRole }}>
      {children}
    </RoleContext.Provider>
  );
}

export function useRole() {
  return useContext(RoleContext);
}
