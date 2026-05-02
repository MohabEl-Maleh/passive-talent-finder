import axios from "axios";

const API = axios.create({ baseURL: "/api" });

// ── Jobs ──────────────────────────────────────────────────────
export const createJob  = (data)   => API.post("/jobs/", data);
export const listJobs   = ()       => API.get("/jobs/");
export const getJob     = (jobId)  => API.get(`/jobs/${jobId}`);
export const deleteJob  = (jobId)  => API.delete(`/jobs/${jobId}`);

// ── CV Upload ─────────────────────────────────────────────────
export const uploadCVs = (jobId, files, mode) => {
  const form = new FormData();
  form.append("upload_mode", mode);
  files.forEach(f => form.append("files", f));
  return API.post(`/cvs/${jobId}/upload`, form, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 300000, // 5 min timeout for large uploads
  });
};

export const getDatasetHistory = (jobId) => API.get(`/cvs/${jobId}/dataset-history`);
export const getCandidateCount = (jobId) => API.get(`/cvs/${jobId}/count`);

// ── AI Matching ───────────────────────────────────────────────
export const runMatching = (jobId) => API.post(`/match/${jobId}`, {}, { timeout: 600000 }); // 10 min
export const getResults  = (jobId, filters = {}) => API.get(`/match/${jobId}/results`, { params: filters });

// ── Shortlisting ──────────────────────────────────────────────
export const getShortlist    = (jobId) => API.get(`/shortlist/${jobId}`);
export const updateShortlist = (jobId, candidateId, status) =>
  API.patch(`/shortlist/${jobId}/candidate/${candidateId}?status=${status}`);

// ── Outreach ──────────────────────────────────────────────────
export const initiateOutreach    = (jobId, candidateId) =>
  API.patch(`/outreach/${jobId}/candidate/${candidateId}/initiate`);
export const initiateOutreachAll = (jobId) =>
  API.patch(`/outreach/${jobId}/initiate-all`);
