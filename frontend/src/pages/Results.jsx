import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Layout from "../components/shared/Layout";
import { getResults, getJob, runMatching, updateShortlist } from "../services/api";

function ScoreRing({ score, color = "#2563EB" }) {
  const r = 28, c = 2 * Math.PI * r;
  const pct = Math.min(100, Math.max(0, score || 0));
  return (
    <svg width="70" height="70" viewBox="0 0 70 70">
      <circle cx="35" cy="35" r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="6" />
      <circle cx="35" cy="35" r={r} fill="none" stroke={color} strokeWidth="6"
        strokeDasharray={c} strokeDashoffset={c - (pct / 100) * c}
        strokeLinecap="round" transform="rotate(-90 35 35)" />
      <text x="35" y="39" textAnchor="middle" fill="white"
        style={{ fontSize: 14, fontWeight: 800, fontFamily: "Plus Jakarta Sans" }}>
        {Math.round(pct)}
      </text>
    </svg>
  );
}

function ExplainPanel({ breakdown, onClose }) {
  if (!breakdown) return null;
  const factors = breakdown.factors || [];
  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", zIndex: 300,
      display: "flex", alignItems: "flex-start", justifyContent: "center",
      padding: "24px", overflowY: "auto",
    }} onClick={onClose}>
      <div style={{
        background: "var(--navy-2)", borderRadius: 20, padding: 28,
        maxWidth: 560, width: "100%", border: "1px solid var(--border-2)",
        marginTop: 40,
      }} onClick={e => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <h3 style={{ fontFamily: "Plus Jakarta Sans", fontWeight: 700, fontSize: 18, color: "var(--text-1)" }}>
            Score Breakdown
          </h3>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "var(--text-3)", cursor: "pointer", fontSize: 24 }}>×</button>
        </div>

        {/* Fit Score Only */}
        <div style={{ display: "flex", gap: 16, marginBottom: 24 }}>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 32, fontWeight: 800, color: "var(--blue-3)" }}>
              {breakdown.fit_score?.toFixed(0) || "—"}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Job Fit</div>
          </div>
        </div>

        {/* Relevance note */}
        {breakdown.relevance_note && (
          <div style={{ padding: "10px 14px", background: "rgba(239,68,68,0.1)", borderRadius: 10, border: "1px solid rgba(239,68,68,0.2)", fontSize: 12, color: "#FCA5A5", marginBottom: 16 }}>
            {breakdown.relevance_note}
          </div>
        )}

        {/* Qualification match */}
        {breakdown.qualification_match && (
          <div style={{ padding: "10px 14px", background: "rgba(37,99,235,0.08)", borderRadius: 10, border: "1px solid rgba(37,99,235,0.15)", fontSize: 13, color: "var(--text-2)", marginBottom: 16 }}>
            <strong style={{ color: "var(--text-1)" }}>Qualification Match</strong><br />
            {breakdown.qualification_match}
          </div>
        )}

        {/* Score factors */}
        {factors.length > 0 && (
          <div style={{ marginBottom: 20 }}>
            {factors.map((f, i) => (
              <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 12, marginBottom: 12 }}>
                <span style={{ fontSize: 18 }}>{f.icon}</span>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-1)" }}>{f.label}</div>
                  <div style={{ fontSize: 12, color: "var(--text-2)" }}>{f.detail}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* AI Assessment */}
        <div style={{ marginTop: 16, background: "rgba(37,99,235,0.06)", borderRadius: 12, border: "1px solid rgba(37,99,235,0.18)", overflow: "hidden" }}>
          <div style={{ padding: "10px 16px", borderBottom: "1px solid rgba(37,99,235,0.15)", display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 14 }}>🤖</span>
            <span style={{ fontSize: 11, fontWeight: 700, color: "var(--blue-3)", fontFamily: "Plus Jakarta Sans", textTransform: "uppercase", letterSpacing: "0.08em" }}>
              AI Assessment
            </span>
          </div>
          <div style={{ padding: "14px 16px", fontSize: 13, color: "var(--text-2)", lineHeight: 1.8 }}>
            {breakdown.summary || "No AI assessment available for this candidate."}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Results() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [candidates, setCandidates] = useState([]);
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [selected, setSelected] = useState(null);
  const [showIrrelevant, setShowIrrelevant] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [r, j] = await Promise.all([
        getResults(jobId, showIrrelevant),
        getJob(jobId),
      ]);
      setCandidates(r.data || []);
      setJob(j.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [jobId, showIrrelevant]);

  const runAI = async () => {
    setRunning(true);
    try {
      await runMatching(jobId);
      await load();
    } finally {
      setRunning(false);
    }
  };

  const toggleShortlist = async (c) => {
    const next = c.shortlist_status === "shortlisted" ? "none" : "shortlisted";
    await updateShortlist(jobId, c.id, next);
    await load();
  };

  const viewCV = (candidateId, sourceFile) => {
    if (!sourceFile || sourceFile === "csv_import") {
      alert("No individual CV file stored for this candidate.");
      return;
    }
    window.open(`http://localhost:8000/api/files/${candidateId}`, "_blank");
  };

  const fitColor = (score) => score >= 70 ? "#10B981" : score >= 50 ? "#F59E0B" : "#EF4444";

  return (
    <Layout job={job}>
      <div style={{ maxWidth: 900, margin: "0 auto", padding: "32px 20px" }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 28 }}>
          <div>
            <h1 style={{ fontFamily: "Plus Jakarta Sans", fontWeight: 800, fontSize: 24, color: "var(--text-1)", marginBottom: 4 }}>
              Candidate Results
            </h1>
            <p style={{ fontSize: 13, color: "var(--text-3)" }}>
              {job?.title} — {candidates.length} candidates ranked
            </p>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-3)", cursor: "pointer" }}>
              <input type="checkbox" checked={showIrrelevant} onChange={e => setShowIrrelevant(e.target.checked)} />
              Show irrelevant
            </label>
            <button className="btn btn-primary" onClick={runAI} disabled={running} style={{ minWidth: 140 }}>
              {running ? "Running AI..." : "▶ Run AI Matching"}
            </button>
            <button className="btn btn-secondary" onClick={() => navigate(`/job/${jobId}/shortlist`)}>
              View Shortlist
            </button>
          </div>
        </div>

        {/* Candidates */}
        {loading ? (
          <div style={{ textAlign: "center", padding: 60, color: "var(--text-3)" }}>Loading results...</div>
        ) : candidates.length === 0 ? (
          <div style={{ textAlign: "center", padding: 60, color: "var(--text-3)" }}>
            No results yet. Upload CVs and run AI matching.
          </div>
        ) : (
          candidates.map((c, idx) => {
            const breakdown = c.score_breakdown || {};
            const isShortlisted = c.shortlist_status === "shortlisted";
            return (
              <div key={c.id} className="card" style={{
                padding: "20px 24px", marginBottom: 12,
                display: "flex", alignItems: "center", gap: 20,
                opacity: c.is_relevant === false ? 0.6 : 1,
                border: isShortlisted ? "1px solid rgba(37,99,235,0.4)" : undefined,
              }}>
                {/* Rank */}
                <div style={{ minWidth: 32, fontSize: 13, fontWeight: 700, color: "var(--text-3)" }}>
                  #{idx + 1}
                </div>

                {/* Score Ring */}
                <ScoreRing score={c.fit_score} color={fitColor(c.fit_score)} />

                {/* Info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontFamily: "Plus Jakarta Sans", fontWeight: 700, fontSize: 15, color: "var(--text-1)", marginBottom: 2 }}>
                    {c.name || "Unknown Candidate"}
                    <span style={{ fontSize: 11, fontWeight: 500, color: "var(--text-3)", marginLeft: 8 }}>
                      {c.seniority_level}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-3)", marginBottom: 6 }}>
                    {[c.current_title, c.current_company, c.years_experience ? `${Math.round(c.years_experience)}y exp` : null]
                      .filter(Boolean).join(" · ")}
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {(c.skills || "").split(",").slice(0, 5).map((s, i) => (
                      <span key={i} className="badge" style={{ fontSize: 10 }}>{s.trim()}</span>
                    ))}
                  </div>
                </div>

                {/* Score label */}
                <div style={{ textAlign: "center", minWidth: 50 }}>
                  <div style={{ fontSize: 22, fontWeight: 800, color: fitColor(c.fit_score) }}>
                    {Math.round(c.fit_score || 0)}
                  </div>
                  <div style={{ fontSize: 10, color: "var(--text-3)", textTransform: "uppercase" }}>Fit</div>
                </div>

                {/* Actions */}
                <div style={{ display: "flex", gap: 8, flexDirection: "column" }}>
                  <button className="btn btn-secondary" style={{ padding: "6px 12px", fontSize: 11 }}
                    onClick={() => viewCV(c.id, c.source_file)}>
                    View CV
                  </button>
                  <button className="btn btn-secondary" style={{ padding: "6px 12px", fontSize: 11 }}
                    onClick={() => setSelected(breakdown)}>
                    Explain
                  </button>
                  <button
                    className={isShortlisted ? "btn btn-primary" : "btn btn-secondary"}
                    style={{ padding: "6px 12px", fontSize: 11 }}
                    onClick={() => toggleShortlist(c)}>
                    {isShortlisted ? "✓ Shortlisted" : "+ Shortlist"}
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      <ExplainPanel breakdown={selected} onClose={() => setSelected(null)} />
    </Layout>
  );
}
