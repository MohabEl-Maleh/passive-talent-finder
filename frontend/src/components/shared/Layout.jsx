import { useRole } from "../../context/RoleContext";
import { useNavigate, useLocation } from "react-router-dom";
import BackButton from "./BackButton";

const recruiterNav = [
  { label: "New Search", path: "/job-setup" },
];

const hmNav = [
  { label: "Dashboard", path: "/hm-dashboard" },
];

const breadcrumbMap = (pathname, role) => {
  const id = pathname.split("/")[2];
  const base = { "/": "Home" };
  const recruiter = {
    "/job-setup":       [{ l:"Home", p:"/" }, { l:"Job Setup" }],
    [`/upload/${id}`]:  [{ l:"Home", p:"/" }, { l:"Job Setup", p:"/job-setup" }, { l:"Upload CVs" }],
    [`/results/${id}`]: [{ l:"Home", p:"/" }, { l:"Job Setup", p:"/job-setup" }, { l:"Upload CVs", p:`/upload/${id}` }, { l:"Results" }],
    [`/shortlist/${id}`]:[{ l:"Home", p:"/" }, { l:"Job Setup", p:"/job-setup" }, { l:"Results", p:`/results/${id}` }, { l:"Shortlist" }],
  };
  const hm = {
    "/hm-dashboard":        [{ l:"Home", p:"/" }, { l:"Dashboard" }],
    [`/hm-review/${id}`]:   [{ l:"Home", p:"/" }, { l:"Dashboard", p:"/hm-dashboard" }, { l:"Shortlist Review" }],
    [`/results/${id}`]:     [{ l:"Home", p:"/" }, { l:"Dashboard", p:"/hm-dashboard" }, { l:"Candidate Results" }],
  };
  return (role === "hiring_manager" ? hm : recruiter)[pathname] || [];
};

export default function Layout({ children }) {
  const { role, setRole } = useRole();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const crumbs = breadcrumbMap(pathname, role);

  return (
    <div style={{ minHeight:"100vh", background:"var(--navy)" }}>

      {/* ── Top Nav ──────────────────────────────────────────────────────── */}
      <header style={{
        position:"sticky", top:0, zIndex:200,
        background:"rgba(8,13,26,0.85)", backdropFilter:"blur(16px)",
        borderBottom:"1px solid var(--border)",
        height:60, display:"flex", alignItems:"center",
        padding:"0 32px", gap:24, justifyContent:"space-between",
      }}>
        {/* Logo */}
        <div style={{ display:"flex", alignItems:"center", gap:10, cursor:"pointer", flexShrink:0 }}
          onClick={() => navigate("/")}>
          <div style={{
            width:30, height:30, borderRadius:8,
            background:"linear-gradient(135deg, var(--blue), #6366F1)",
            display:"flex", alignItems:"center", justifyContent:"center",
            fontFamily:"Syne", fontWeight:800, fontSize:14, color:"white",
          }}>P</div>
          <span style={{ fontFamily:"Syne", fontWeight:800, fontSize:15, color:"var(--text-1)", letterSpacing:"-0.01em" }}>
            PassiveTalent
          </span>
        </div>

        {/* Nav links */}
        <nav style={{ display:"flex", alignItems:"center", gap:4 }}>
          {(role === "recruiter" ? recruiterNav : hmNav).map(item => (
            <button key={item.path} onClick={() => navigate(item.path)}
              style={{
                background: pathname === item.path ? "var(--navy-4)" : "transparent",
                border: "none", borderRadius:8, padding:"7px 14px",
                color: pathname === item.path ? "var(--text-1)" : "var(--text-2)",
                fontFamily:"Syne", fontWeight:600, fontSize:13,
                cursor:"pointer", transition:"all 0.2s",
              }}>
              {item.label}
            </button>
          ))}
        </nav>

        {/* Right side */}
        <div style={{ display:"flex", alignItems:"center", gap:12 }}>
          <span className="badge badge-blue" style={{ fontSize:10 }}>
            {role === "recruiter" ? "Recruiter" : "Hiring Manager"}
          </span>
          <button className="btn btn-ghost" style={{ padding:"7px 14px", fontSize:12 }}
            onClick={() => { setRole(null); navigate("/"); }}>
            Switch Role
          </button>
        </div>
      </header>

      {/* ── Breadcrumb ───────────────────────────────────────────────────── */}
      {crumbs.length > 1 && (
        <div style={{
          background:"var(--navy-2)", borderBottom:"1px solid var(--border)",
          padding:"9px 32px", display:"flex", alignItems:"center", gap:6,
        }}>
          {crumbs.map((c, i) => (
            <span key={i} style={{ display:"flex", alignItems:"center", gap:6 }}>
              {i > 0 && <span style={{ color:"var(--text-3)", fontSize:11 }}>›</span>}
              {c.p ? (
                <button onClick={() => navigate(c.p)} style={{
                  background:"none", border:"none", cursor:"pointer",
                  color:"var(--blue-3)", fontSize:12, fontFamily:"Syne", fontWeight:600, padding:0,
                }}>{c.l}</button>
              ) : (
                <span style={{ color:"var(--text-1)", fontSize:12, fontFamily:"Syne", fontWeight:700 }}>{c.l}</span>
              )}
            </span>
          ))}
        </div>
      )}

      {/* ── Page content ─────────────────────────────────────────────────── */}
      <main style={{ maxWidth:1240, margin:"0 auto", padding:"44px 32px" }}>
        <BackButton />
        {children}
      </main>
    </div>
  );
}
