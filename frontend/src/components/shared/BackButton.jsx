import { useNavigate } from "react-router-dom";

export default function BackButton({ to }) {
  const navigate = useNavigate();
  return (
    <button
      type="button"
      onClick={() => (to ? navigate(to) : navigate(-1))}
      style={{
        display: "inline-flex", alignItems: "center", gap: 6,
        background: "transparent", border: "none",
        color: "var(--text-secondary)", cursor: "pointer",
        fontFamily: "Plus Jakarta Sans", fontWeight: 600,
        fontSize: 14, padding: "8px 0", marginBottom: 24,
        transition: "color 0.2s",
      }}
      onMouseEnter={e => e.currentTarget.style.color = "var(--text-primary)"}
      onMouseLeave={e => e.currentTarget.style.color = "var(--text-secondary)"}
    >
      Back
    </button>
  );
}
