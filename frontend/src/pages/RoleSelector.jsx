import { useRole } from "../context/RoleContext";
import { useNavigate } from "react-router-dom";
import BackButton from "../components/shared/BackButton";

const STATS = [
  { value: "2,484", label: "CVs in dataset" },
  { value: "2-Layer", label: "AI scoring engine" },
  { value: "100%", label: "Classifier accuracy" },
  { value: "5", label: "Test cases covered" },
];

const FEATURES = [
  { icon: "🔍", title: "Passive Talent Detection", desc: "Identifies candidates who are employed and not actively searching — the underutilised majority of the talent pool." },
  { icon: "🧠", title: "Dual-Score AI Engine", desc: "Job-fit score via semantic similarity + passivity indicator via career signal analysis. Two independent, transparent scores." },
  { icon: "📊", title: "Explainable Rankings", desc: "Every ranking comes with a full breakdown — qualification match, outreach difficulty, and actionable summary." },
  { icon: "⚖️", title: "Fairness by Design", desc: "Passivity does not affect ranking. Candidates are scored purely on qualification match." },
];

export default function RoleSelector() {
  const { setRole } = useRole();
  const navigate = useNavigate();

  const select = (role) => {
    setRole(role);
    navigate(role === "recruiter" ? "/job-setup" : "/hm-dashboard");
  };

  return (
    <div style={{ minHeight: "100vh", background: "var(--navy)", display: "flex", flexDirection: "column" }}>

      {/* Nav */}
      <header style={{
        height: 60, display: "flex", alignItems: "center", padding: "0 48px",
        borderBottom: "1px solid var(--border)",
        background: "rgba(8,13,26,0.9)", backdropFilter: "blur(12px)",
        position: "sticky", top: 0, zIndex: 100, justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 28, height: 28, borderRadius: 7,
            background: "linear-gradient(135deg, #2563EB, #6366F1)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 13, fontWeight: 700, color: "white", fontFamily: "Plus Jakarta Sans",
          }}>P</div>
          <span style={{ fontFamily: "Plus Jakarta Sans", fontWeight: 700, fontSize: 15, color: "var(--text-1)", letterSpacing: "-0.01em" }}>
            PassiveTalent
          </span>
        </div>
        <span style={{ fontSize: 12, color: "var(--text-3)", fontFamily: "DM Sans" }}>
          GUC Graduation Project · 2026
        </span>
      </header>

      <main style={{ flex: 1, maxWidth: 1100, margin: "0 auto", padding: "24px 40px 0", width: "100%" }}>
        <BackButton />

        {/* Hero */}
        <div style={{ textAlign: "center", padding: "72px 0 56px", animation: "fadeUp 0.6s ease both" }}>

          <div style={{
            display: "inline-flex", alignItems: "center", gap: 8,
            background: "rgba(37,99,235,0.1)", border: "1px solid rgba(37,99,235,0.2)",
            borderRadius: 20, padding: "5px 14px", marginBottom: 28,
          }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#3B82F6" }} />
            <span style={{ fontSize: 12, color: "#60A5FA", fontFamily: "Plus Jakarta Sans", fontWeight: 600, letterSpacing: "0.04em" }}>
              PREDICTIVE AI FOR HEADHUNTING
            </span>
          </div>

          <h1 style={{
            fontFamily: "Plus Jakarta Sans", fontWeight: 700,
            fontSize: "clamp(28px, 4vw, 44px)",
            color: "var(--text-1)", lineHeight: 1.2,
            marginBottom: 18, letterSpacing: "-0.02em", maxWidth: 640, margin: "0 auto 18px",
          }}>
            Identify and Rank Passive Talent in Large Networks
          </h1>

          <p style={{
            fontSize: 16, color: "var(--text-2)", maxWidth: 520,
            margin: "0 auto 52px", lineHeight: 1.7, fontWeight: 400,
          }}>
            An AI-powered headhunting system that finds the best candidates from your CV dataset —
            including those who aren't actively looking.
          </p>

          {/* Stats */}
          <div style={{
            display: "inline-flex", gap: 0,
            background: "var(--navy-2)", border: "1px solid var(--border)",
            borderRadius: 14, overflow: "hidden", marginBottom: 56,
          }}>
            {STATS.map((s, i) => (
              <div key={i} style={{
                padding: "16px 28px",
                borderRight: i < STATS.length - 1 ? "1px solid var(--border)" : "none",
                animation: `fadeUp 0.5s ease ${0.1 + i * 0.07}s both`,
              }}>
                <div style={{ fontFamily: "Plus Jakarta Sans", fontWeight: 700, fontSize: 22, color: "var(--text-1)" }}>{s.value}</div>
                <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 3, fontFamily: "Plus Jakarta Sans", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>{s.label}</div>
              </div>
            ))}
          </div>

          {/* Role cards */}
          <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap", marginBottom: 72 }}>
            {[
              {
                role: "recruiter", icon: "🔍", title: "Recruiter",
                desc: "Upload CVs, run AI matching, view ranked results, manage shortlists and initiate outreach.",
                accent: "#3B82F6", bg: "rgba(37,99,235,0.08)", border: "rgba(37,99,235,0.2)", cta: "Start Recruiting →",
              },
              {
                role: "hiring_manager", icon: "📋", title: "Hiring Manager",
                desc: "Review AI-ranked shortlists, approve or reject candidates, and provide feedback to refine search.",
                accent: "#14B8A6", bg: "rgba(13,148,136,0.08)", border: "rgba(13,148,136,0.2)", cta: "Review Shortlists →",
              },
            ].map((r, i) => (
              <button key={r.role} onClick={() => select(r.role)} style={{
                background: "var(--navy-2)", border: "1px solid var(--border)",
                borderRadius: 16, padding: "28px 32px", cursor: "pointer",
                width: 260, textAlign: "left", transition: "all 0.2s",
                animation: `fadeUp 0.5s ease ${0.3 + i * 0.1}s both`,
              }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = r.border;
                  e.currentTarget.style.background = r.bg;
                  e.currentTarget.style.transform = "translateY(-4px)";
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = "var(--border)";
                  e.currentTarget.style.background = "var(--navy-2)";
                  e.currentTarget.style.transform = "translateY(0)";
                }}>
                <div style={{ fontSize: 24, marginBottom: 14 }}>{r.icon}</div>
                <div style={{ fontFamily: "Plus Jakarta Sans", fontWeight: 700, fontSize: 17, color: "var(--text-1)", marginBottom: 8 }}>{r.title}</div>
                <div style={{ fontSize: 13, color: "var(--text-2)", lineHeight: 1.65, marginBottom: 20 }}>{r.desc}</div>
                <div style={{ fontSize: 13, color: r.accent, fontFamily: "Plus Jakarta Sans", fontWeight: 600 }}>{r.cta}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Features */}
        <div style={{ borderTop: "1px solid var(--border)", paddingTop: 56, marginBottom: 56 }}>
          <p style={{ fontSize: 11, color: "var(--text-3)", fontFamily: "Plus Jakarta Sans", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 10 }}>
            Core Capabilities
          </p>
          <h2 style={{ fontFamily: "Plus Jakarta Sans", fontWeight: 700, fontSize: 24, color: "var(--text-1)", marginBottom: 32 }}>
            What makes this system different
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 16 }}>
            {FEATURES.map((f, i) => (
              <div key={i} className="card" style={{ padding: 24, animation: `fadeUp 0.5s ease ${0.1 + i * 0.07}s both` }}>
                <div style={{ fontSize: 24, marginBottom: 14 }}>{f.icon}</div>
                <div style={{ fontFamily: "Plus Jakarta Sans", fontWeight: 600, fontSize: 15, color: "var(--text-1)", marginBottom: 8 }}>{f.title}</div>
                <div style={{ fontSize: 13, color: "var(--text-2)", lineHeight: 1.7 }}>{f.desc}</div>
              </div>
            ))}
          </div>
        </div>


      </main>

      <footer style={{ borderTop: "1px solid var(--border)", padding: "18px 48px", textAlign: "center" }}>
        <span style={{ fontSize: 12, color: "var(--text-3)", fontFamily: "DM Sans" }}>
          Mohab El-Maleh · German University in Cairo · Faculty of Management Technology · 2026
        </span>
      </footer>
    </div>
  );
}
