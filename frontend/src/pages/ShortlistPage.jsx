import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getShortlist, updateShortlist, initiateOutreach, initiateOutreachAll } from "../services/api";
import { useRole } from "../context/RoleContext";

export default function ShortlistPage() {
  const { jobId } = useParams();
  const { role } = useRole();
  const navigate = useNavigate();
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [outreachMessage, setOutreachMessage] = useState(null);
  const [outreachCandidate, setOutreachCandidate] = useState(null);

  const load = () => {
    getShortlist(jobId).then(r => setCandidates(r.data)).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, [jobId]);

  const updateStatus = async (id, status) => { await updateShortlist(jobId, id, status); load(); };
  const removeFromShortlist = async (id) => { await updateShortlist(jobId, id, "pending"); load(); };
  const startOutreach = async (id) => {
    const res = await initiateOutreach(jobId, id);
    if (res.data.outreach_message) {
      setOutreachMessage(res.data.outreach_message);
      setOutreachCandidate(res.data.candidate);
    }
    load();
  };
  const startAll = async () => { await initiateOutreachAll(jobId); load(); };
  const clearAll = async () => {
    if (window.confirm("Remove all candidates from this shortlist?")) {
      for (const c of candidates) await updateShortlist(jobId, c.id, "pending");
      load();
    }
  };

  const approved = candidates.filter(c => c.shortlist_status === "approved");
  const rejected = candidates.filter(c => c.shortlist_status === "rejected");

  if (loading) return <div style={{ textAlign: "center", padding: 80, color: "var(--text-secondary)" }}>Loading shortlist...</div>;

  return (
    <div style={{ animation: "fadeUp 0.5s ease" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 36 }}>
        <div>
          <div className={`badge ${role === "hiring_manager" ? "badge-teal" : "badge-blue"}`} style={{ marginBottom: 12 }}>
            {role === "hiring_manager" ? "Hiring Manager Review" : "Shortlist Management"}
          </div>
          <h1 style={{ fontFamily: "Plus Jakarta Sans", fontWeight: 800, fontSize: 32, color: "var(--text-primary)", marginBottom: 6 }}>Candidate Shortlist</h1>
          <p style={{ color: "var(--text-secondary)", fontSize: 15 }}>
            {approved.length} approved · {rejected.length} rejected · {candidates.length - approved.length - rejected.length} pending
          </p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          {candidates.length > 0 && (
            <button className="btn-secondary" style={{ borderColor: "rgba(239,68,68,0.3)", color: "#FCA5A5" }} onClick={clearAll}>Clear All</button>
          )}
          {approved.length > 0 && role === "recruiter" && (
            <button className="btn-primary" onClick={startAll}>Initiate Outreach ({approved.length})</button>
          )}
        </div>
      </div>

      {candidates.length === 0 ? (
        <div className="card" style={{ padding: 60, textAlign: "center" }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>📋</div>
          <div style={{ fontFamily: "Plus Jakarta Sans", fontSize: 18, color: "var(--text-primary)", marginBottom: 8 }}>No candidates shortlisted yet</div>
          <div style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 20 }}>Go to the Results page and click "+ Shortlist" on candidates you want to review.</div>
          <button className="btn-primary" onClick={() => navigate(`/results/${jobId}`)}>Go to Results</button>
        </div>
      ) : (
        <div style={{ display: "grid", gap: 14 }}>
          {candidates.map((c, i) => (
            <div key={c.id} className="card" style={{
              padding: "24px 28px", position: "relative",
              borderColor: c.shortlist_status === "approved" ? "rgba(20,184,166,0.3)" : c.shortlist_status === "rejected" ? "rgba(239,68,68,0.2)" : "var(--border)",
              animation: `fadeUp 0.4s ease ${i * 0.05}s both`,
            }}>
              <button onClick={() => removeFromShortlist(c.id)} style={{
                position: "absolute", top: 12, right: 12,
                background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)",
                borderRadius: 6, width: 28, height: 28, cursor: "pointer",
                color: "#FCA5A5", fontSize: 16, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700,
              }}>×</button>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 20, paddingRight: 36 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6, flexWrap: "wrap" }}>
                    <span style={{ fontFamily: "Plus Jakarta Sans", fontWeight: 700, fontSize: 17, color: "var(--text-primary)" }}>{c.name || `Candidate ${c.id}`}</span>
                    <span className={`badge ${c.shortlist_status === "approved" ? "badge-teal" : c.shortlist_status === "rejected" ? "badge-red" : "badge-gray"}`}>{c.shortlist_status}</span>
                    {c.outreach_status === "initiated" && <span className="badge badge-blue">Outreach initiated</span>}
                  </div>
                  <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 4 }}>
                    {c.current_title && <span>{c.current_title} · </span>}
                    Fit Score: <strong style={{ color: "var(--blue)" }}>{c.fit_score?.toFixed(0)}/100</strong>
                  </div>
                  {c.score_breakdown?.summary && <div style={{ fontSize: 12, color: "var(--text-muted)", lineHeight: 1.5 }}>{c.score_breakdown.summary}</div>}
                </div>
                <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
                  {role === "hiring_manager" ? (
                    <>
                      <button className="btn-primary" style={{ background: "rgba(20,184,166,0.2)", color: "#2DD4BF", padding: "8px 16px", fontSize: 13 }} onClick={() => updateStatus(c.id, "approved")}>✓ Approve</button>
                      <button className="btn-secondary" style={{ borderColor: "rgba(239,68,68,0.3)", color: "#FCA5A5", padding: "8px 16px", fontSize: 13 }} onClick={() => updateStatus(c.id, "rejected")}>✗ Reject</button>
                    </>
                  ) : (
                    c.shortlist_status === "approved" && c.outreach_status === "pending" && (
                      <button className="btn-primary" style={{ padding: "8px 16px", fontSize: 13 }} onClick={() => startOutreach(c.id)}>Initiate Outreach</button>
                    )
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      {/* Outreach Message Modal */}
      {outreachMessage && (
        <div style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", zIndex: 300,
          display: "flex", alignItems: "center", justifyContent: "center", padding: 24,
          animation: "fadeIn 0.2s ease",
        }} onClick={() => setOutreachMessage(null)}>
          <div style={{
            background: "var(--navy-2)", borderRadius: 20, padding: 40,
            maxWidth: 600, width: "100%", border: "1px solid var(--border-2)",
            maxHeight: "80vh", overflowY: "auto",
          }} onClick={e => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
              <h3 style={{ fontFamily: "Plus Jakarta Sans", fontWeight: 700, fontSize: 18, color: "var(--text-1)" }}>
                📧 Outreach Message — {outreachCandidate}
              </h3>
              <button onClick={() => setOutreachMessage(null)} style={{ background: "none", border: "none", color: "var(--text-3)", cursor: "pointer", fontSize: 22 }}>×</button>
            </div>
            <div style={{ background: "var(--navy-3)", borderRadius: 12, padding: 20, border: "1px solid var(--border)", fontSize: 13, color: "var(--text-2)", lineHeight: 1.8, whiteSpace: "pre-wrap" }}>
              {outreachMessage}
            </div>
            <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
              <button className="btn btn-primary" style={{ flex: 1 }}
                onClick={() => { navigator.clipboard.writeText(outreachMessage); }}>
                Copy to Clipboard
              </button>
              <button className="btn btn-secondary" onClick={() => setOutreachMessage(null)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
