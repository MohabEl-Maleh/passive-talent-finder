import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { listJobs, deleteJob } from "../services/api";

export default function HMDashboard() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState([]);

  useEffect(() => {
    listJobs().then(r => {
      const seen = new Map();
      r.data.forEach(j => {
        if (!seen.has(j.title) || j.id > seen.get(j.title).id) seen.set(j.title, j);
      });
      setJobs(Array.from(seen.values()));
    }).catch(() => {});
  }, []);

  const handleDelete = async (e, jobId) => {
    e.stopPropagation();
    if (window.confirm("Delete this job and all its candidates?")) {
      await deleteJob(jobId);
      setJobs(prev => prev.filter(j => j.id !== jobId));
    }
  };

  return (
    <div style={{ animation: "fadeUp 0.5s ease" }}>
      <div style={{ marginBottom: 40 }}>
        <div className="badge badge-teal" style={{ marginBottom: 16 }}>Hiring Manager</div>
        <h1 style={{ fontFamily: "Plus Jakarta Sans", fontWeight: 800, fontSize: 36, color: "var(--text-primary)", marginBottom: 8 }}>Candidate Shortlists</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: 16 }}>Review and approve shortlisted candidates for each open position.</p>
      </div>

      {jobs.length === 0 ? (
        <div className="card" style={{ padding: 60, textAlign: "center" }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>📋</div>
          <div style={{ fontFamily: "Plus Jakarta Sans", fontSize: 18, color: "var(--text-primary)", marginBottom: 8 }}>No positions yet</div>
          <div style={{ color: "var(--text-secondary)", fontSize: 14 }}>A recruiter needs to create a job and shortlist candidates first.</div>
        </div>
      ) : (
        <div style={{ display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))" }}>
          {jobs.map((j, i) => (
            <div key={j.id} className="card" style={{
              padding: 28, position: "relative",
              animation: `fadeUp 0.4s ease ${i * 0.08}s both`,
              transition: "all 0.2s", cursor: "pointer",
            }}
            onClick={() => navigate(`/hm-review/${j.id}`)}
            onMouseEnter={e => { e.currentTarget.style.borderColor = "rgba(20,184,166,0.4)"; e.currentTarget.style.transform = "translateY(-2px)"; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.transform = "translateY(0)"; }}>
              <button onClick={e => handleDelete(e, j.id)} style={{
                position: "absolute", top: 12, right: 12,
                background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)",
                borderRadius: 6, width: 28, height: 28, cursor: "pointer",
                color: "#FCA5A5", fontSize: 16, display: "flex",
                alignItems: "center", justifyContent: "center", fontWeight: 700,
              }}>×</button>
              <div style={{ fontFamily: "Plus Jakarta Sans", fontWeight: 700, fontSize: 18, color: "var(--text-primary)", marginBottom: 6, paddingRight: 36 }}>{j.title}</div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 6 }}>
                {j.industry}{j.min_experience > 0 && ` · ${j.min_experience}+ years exp`}
              </div>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 24, lineHeight: 1.5 }}>{j.required_skills?.slice(0, 80)}...</div>
              <button className="btn-primary" style={{ width: "100%", padding: "12px", fontSize: 14, marginBottom: 8 }}
                onClick={e => { e.stopPropagation(); navigate(`/hm-review/${j.id}`); }}>
                Review Shortlist →
              </button>
              <button className="btn-secondary" style={{ width: "100%", padding: "8px", fontSize: 12 }}
                onClick={e => { e.stopPropagation(); navigate(`/results/${j.id}`); }}>
                View all candidates
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
