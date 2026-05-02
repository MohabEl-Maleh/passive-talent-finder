import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createJob } from "../services/api";

export default function JobSetup() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    title: "", description: "", required_skills: "",
    min_experience: 0, industry: "",
  });
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.title || !form.required_skills) return alert("Please fill in job title and required skills.");
    setLoading(true);
    try {
      const res = await createJob(form);
      navigate(`/upload/${res.data.id}`);
    } catch { alert("Error creating job. Make sure the backend is running."); }
    finally { setLoading(false); }
  };

  return (
    <div style={{ maxWidth: 720, margin: "0 auto", animation: "fadeUp 0.5s ease" }}>
      <div style={{ marginBottom: 40 }}>
        <div className="badge badge-blue" style={{ marginBottom: 16 }}>Step 1 of 3</div>
        <h1 style={{ fontFamily: "Plus Jakarta Sans", fontWeight: 800, fontSize: 36, color: "var(--text-primary)", marginBottom: 8 }}>Define the Position</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: 16 }}>Describe what you're looking for — the AI uses this to score every candidate.</p>
      </div>
      <div className="card" style={{ padding: 40 }}>
        <div style={{ display: "grid", gap: 28 }}>
          <div>
            <label className="label">Job Title *</label>
            <input className="input" placeholder="e.g. Senior Backend Engineer" value={form.title} onChange={e => set("title", e.target.value)} />
          </div>
          <div>
            <label className="label">Job Description</label>
            <textarea className="input" placeholder="Describe the role and responsibilities..." rows={4} value={form.description} onChange={e => set("description", e.target.value)} style={{ resize: "vertical" }} />
          </div>
          <div>
            <label className="label">Required Skills *</label>
            <input className="input" placeholder="e.g. Python, Machine Learning, SQL" value={form.required_skills} onChange={e => set("required_skills", e.target.value)} />
            <p style={{ color: "var(--text-muted)", fontSize: 12, marginTop: 6 }}>Comma-separated. The AI uses these to compute the job-fit score.</p>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
            <div>
              <label className="label">Minimum Experience (years)</label>
              <input className="input" type="number" min={0} max={30} value={form.min_experience} onChange={e => set("min_experience", parseInt(e.target.value) || 0)} />
            </div>
            <div>
              <label className="label">Industry</label>
              <input className="input" placeholder="e.g. Technology, Finance" value={form.industry} onChange={e => set("industry", e.target.value)} />
            </div>
          </div>
          <div style={{ background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.2)", borderRadius: 12, padding: "16px 20px", display: "flex", gap: 12 }}>
            <span style={{ fontSize: 18 }}>💡</span>
            <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
              Candidates are ranked by <strong style={{ color: "var(--text-primary)" }}>job-fit score</strong>. A separate <strong style={{ color: "var(--text-primary)" }}>passivity indicator</strong> shows outreach difficulty.
            </div>
          </div>
        </div>
      </div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 24 }}>
        <button className="btn-primary" onClick={submit} disabled={loading} style={{ minWidth: 180 }}>
          {loading ? "Creating..." : "Next: Upload CVs →"}
        </button>
      </div>
    </div>
  );
}
