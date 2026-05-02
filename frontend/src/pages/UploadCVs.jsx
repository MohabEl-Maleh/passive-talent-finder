import { useState, useCallback, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { uploadCVs, runMatching, getDatasetHistory, getCandidateCount } from "../services/api";

export default function UploadCVs() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [files, setFiles] = useState([]);
  const [mode, setMode] = useState("fresh");
  const [uploading, setUploading] = useState(false);
  const [running, setRunning] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [count, setCount] = useState(0);
  const [dragging, setDragging] = useState(false);

  const reload = () => {
    getDatasetHistory(jobId).then(r => setHistory(r.data)).catch(() => { });
    getCandidateCount(jobId).then(r => setCount(r.data.total_candidates)).catch(() => { });
  };
  useEffect(() => { reload(); }, [jobId]);

  const onDrop = useCallback((e) => {
    e.preventDefault(); setDragging(false);
    const dropped = Array.from(e.dataTransfer?.files || e.target.files || []);
    setFiles(f => [...f, ...dropped]);
  }, []);

  const upload = async () => {
    if (!files.length) return alert("Please select at least one file.");
    setUploading(true);
    try {
      const res = await uploadCVs(jobId, files, mode);
      setUploadResult(res.data);
      setFiles([]);
      reload();
    } catch (e) {
      alert("Upload failed. Make sure the backend is running.");
    } finally { setUploading(false); }
  };

  const runAI = async () => {
    if (count === 0) return alert("Please upload some CVs first.");
    setRunning(true);
    try {
      await runMatching(jobId);
      navigate(`/results/${jobId}`);
    } catch (e) {
      alert("AI matching failed: " + (e.response?.data?.detail || e.message));
    } finally { setRunning(false); }
  };

  return (
    <div style={{ maxWidth: 720, margin: "0 auto", animation: "fadeUp 0.5s ease" }}>
      <button onClick={() => navigate('/job-setup')} style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontFamily: 'Plus Jakarta Sans', fontWeight: 600, fontSize: 14, marginBottom: 24, padding: '8px 0' }}>Back</button>

      <div style={{ marginBottom: 40 }}>
        <div className="badge badge-blue" style={{ marginBottom: 16 }}>Step 2 of 3</div>
        <h1 style={{ fontFamily: "Plus Jakarta Sans", fontWeight: 800, fontSize: 36, color: "var(--text-primary)", marginBottom: 8 }}>
          Upload CV Dataset
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: 16 }}>
          Upload CVs from any source — individual files or a full CSV dataset.
        </p>
      </div>

      <div className="card" style={{ padding: 40, display: "grid", gap: 28 }}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {[
            { icon: "📄", label: "PDF files", desc: "Individual CVs" },
            { icon: "📝", label: "DOCX files", desc: "Word documents" },
            { icon: "📊", label: "CSV file", desc: "Kaggle-style dataset" },
            { icon: "📃", label: "TXT files", desc: "Plain text CVs" },
          ].map(f => (
            <div key={f.label} style={{
              flex: "1 1 140px", background: "var(--navy-3)", borderRadius: 10,
              padding: "12px 14px", border: "1px solid var(--border)",
              display: "flex", alignItems: "center", gap: 10,
            }}>
              <span style={{ fontSize: 20 }}>{f.icon}</span>
              <div>
                <div style={{ fontSize: 13, fontFamily: "Plus Jakarta Sans", fontWeight: 600, color: "var(--text-primary)" }}>{f.label}</div>
                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{f.desc}</div>
              </div>
            </div>
          ))}
        </div>

        <div>
          <label className="label">Upload Mode</label>
          <div style={{ display: "flex", gap: 12 }}>
            {[
              { id: "fresh", icon: "🔄", label: "Fresh Upload", desc: "Replace all existing CVs" },
              { id: "append", icon: "➕", label: "Append / Update", desc: "Add new CVs, skip duplicates" },
            ].map(m => (
              <button key={m.id} onClick={() => setMode(m.id)} style={{
                flex: 1, padding: "14px 16px", borderRadius: 10, cursor: "pointer",
                border: `1px solid ${mode === m.id ? "var(--blue)" : "var(--border)"}`,
                background: mode === m.id ? "rgba(59,130,246,0.1)" : "var(--navy-3)",
                color: mode === m.id ? "#60A5FA" : "var(--text-secondary)",
                fontFamily: "Plus Jakarta Sans", fontWeight: 600, fontSize: 14,
                transition: "all 0.2s", textAlign: "left",
              }}>
                <div>{m.icon} {m.label}</div>
                <div style={{ fontSize: 11, fontWeight: 400, marginTop: 4, opacity: 0.8 }}>{m.desc}</div>
              </button>
            ))}
          </div>
        </div>

        <div
          onDrop={onDrop} onDragOver={e => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onClick={() => document.getElementById("file-input").click()}
          style={{
            border: `2px dashed ${dragging ? "var(--blue)" : "var(--border)"}`,
            borderRadius: 14, padding: "52px 32px", textAlign: "center",
            cursor: "pointer", transition: "all 0.2s",
            background: dragging ? "rgba(59,130,246,0.05)" : "var(--navy-3)",
          }}>
          <input id="file-input" type="file" multiple accept=".pdf,.docx,.txt,.csv"
            style={{ display: "none" }} onChange={onDrop} />
          <div style={{ fontSize: 44, marginBottom: 14 }}>📂</div>
          <div style={{ fontFamily: "Plus Jakarta Sans", fontWeight: 700, fontSize: 17, color: "var(--text-primary)", marginBottom: 6 }}>
            Drop files here or click to browse
          </div>
          <div style={{ color: "var(--text-muted)", fontSize: 13, lineHeight: 1.6 }}>
            Supports <strong style={{ color: "var(--text-secondary)" }}>PDF, DOCX, TXT</strong> — upload multiple CV files at once<br/>
            Or upload your <strong style={{ color: "var(--text-secondary)" }}>Resume.csv</strong> Kaggle dataset to load all 2,484 resumes at once
          </div>
          <div style={{ marginTop: 16 }} onClick={e => e.stopPropagation()}>
            <button onClick={() => document.getElementById("file-input").click()}
              style={{
                background: "rgba(59,130,246,0.15)", border: "1px solid rgba(59,130,246,0.3)",
                borderRadius: 8, padding: "10px 24px", cursor: "pointer",
                color: "#60A5FA", fontSize: 13, fontFamily: "Plus Jakarta Sans", fontWeight: 600,
              }}>
              Browse Files
            </button>
            <div style={{ color: "var(--text-muted)", fontSize: 11, marginTop: 8 }}>
              Tip: Hold Ctrl and click to select multiple files at once
            </div>
          </div>
        </div>

        {files.length > 0 && (
          <div style={{ display: "grid", gap: 8 }}>
            <label className="label">{files.length} file{files.length > 1 ? "s" : ""} ready to upload</label>
            <div style={{ maxHeight: 200, overflowY: "auto", display: "grid", gap: 6 }}>
              {files.map((f, i) => (
                <div key={i} style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  background: "var(--navy-3)", borderRadius: 8, padding: "10px 14px",
                  border: "1px solid var(--border)",
                }}>
                  <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                    {f.name.endsWith(".csv") ? "📊" : f.name.endsWith(".pdf") ? "📄" : "📝"} {f.name}
                    <span style={{ color: "var(--text-muted)", marginLeft: 8, fontSize: 11 }}>{(f.size / 1024).toFixed(0)} KB</span>
                  </span>
                  <button onClick={() => setFiles(fs => fs.filter((_, j) => j !== i))}
                    style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: 18 }}>×</button>
                </div>
              ))}
            </div>
            <button className="btn-primary" onClick={upload} disabled={uploading}>
              {uploading ? "⏳ Uploading and parsing CVs..." : `Upload ${files.length} file${files.length > 1 ? "s" : ""}`}
            </button>
          </div>
        )}

        {uploadResult && (
          <div style={{ background: "rgba(20,184,166,0.08)", border: "1px solid rgba(20,184,166,0.2)", borderRadius: 12, padding: "16px 20px" }}>
            <div style={{ fontFamily: "Plus Jakarta Sans", fontWeight: 700, color: "#2DD4BF", marginBottom: 10 }}>✓ Upload complete</div>
            <div style={{ display: "flex", gap: 28, fontSize: 14, color: "var(--text-secondary)" }}>
              <span>CVs added: <strong style={{ color: "var(--text-primary)", fontSize: 18 }}>{uploadResult.candidates_added}</strong></span>
              <span>Duplicates skipped: <strong style={{ color: "var(--text-primary)" }}>{uploadResult.duplicates_skipped}</strong></span>
            </div>
          </div>
        )}

        {count > 0 && (
          <div style={{ background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.15)", borderRadius: 12, padding: "14px 20px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: 14, color: "var(--text-secondary)" }}>Total CVs loaded for this job:</span>
            <span style={{ fontFamily: "Plus Jakarta Sans", fontWeight: 700, fontSize: 22, color: "#60A5FA" }}>{count}</span>
          </div>
        )}

        {history.length > 0 && (
          <div>
            <label className="label">Upload history</label>
            <div style={{ display: "grid", gap: 6 }}>
              {history.slice(0, 3).map((h, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "var(--navy-3)", borderRadius: 8, padding: "10px 14px", border: "1px solid var(--border)", fontSize: 12, color: "var(--text-secondary)" }}>
                  <span>{h.upload_mode === "fresh" ? "🔄" : "➕"} {h.upload_mode} — {h.added} added, {h.skipped} skipped</span>
                  <span style={{ color: "var(--text-muted)" }}>{new Date(h.uploaded_at).toLocaleDateString()}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div style={{ marginTop: 24, display: "flex", justifyContent: "flex-end" }}>
        <button className="btn-primary" onClick={runAI} disabled={running || count === 0}
          style={{ minWidth: 220, opacity: count === 0 ? 0.5 : 1 }}>
          {running ? "⚙️ Running AI matching..." : count > 0 ? `🚀 Run AI on ${count} CVs →` : "Upload CVs first"}
        </button>
      </div>
    </div>
  );
}
