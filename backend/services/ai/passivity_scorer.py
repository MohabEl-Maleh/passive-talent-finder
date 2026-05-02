# backend/services/ai/passivity_scorer.py
#
# THE CORE RESEARCH CONTRIBUTION
# ================================
# Computes a Passivity Score (0–100) for each candidate.
#
# A high score means the candidate is likely:
#   - Currently employed
#   - Stable in their current role (long tenure)
#   - Not a frequent job-hopper (few changes)
#   - Senior enough that they're rarely on the market
#
# This is what separates this system from all existing AI recruitment tools,
# which only process active job seekers.
#
# IMPORTANT DESIGN DECISION:
# ===========================
# The passivity score is PURELY INFORMATIONAL.
# It does NOT affect candidate ranking or the composite score.
# Candidates are ranked 100% on job-fit (qualification match).
#
# The passivity score is shown separately on each candidate card
# as a "headhunting context" indicator — it tells the recruiter
# how hard this person may be to engage, not whether they are qualified.
#
# Academic rationale: penalizing passive candidates for being passive
# would be self-defeating — the entire point of headhunting is to
# reach people who are NOT actively looking. Their passivity is a
# feature of the target pool, not a disqualifier.
#
# Formula (weighted sum, normalized to 0–100):
#   Passivity = 0.35 × tenure_score
#             + 0.30 × employment_score
#             + 0.20 × stability_score
#             + 0.15 × seniority_score


def compute_passivity_score(
    tenure_months: float,
    is_employed: int,
    job_changes: int,
    seniority_level: str,
) -> float:
    """
    Compute a passivity score from 0 to 100.

    Args:
        tenure_months:   Estimated months at current/most recent job
        is_employed:     1 if currently employed, 0 if not
        job_changes:     Number of job transitions in career
        seniority_level: "junior" | "mid" | "senior" (or None)

    Returns:
        float: Passivity score 0–100 (higher = more passive)
    """

    # ── Sub-score 1: Tenure (0–100) ──────────────────────────────────────────
    # 0 months  → score 0
    # 12 months → score ~33
    # 24 months → score ~67
    # 36+ months → score 100 (cap)
    tenure_score = min(100.0, (tenure_months / 36.0) * 100.0)

    # ── Sub-score 2: Employment status (0–100) ───────────────────────────────
    # Currently employed → 100 (strong passivity signal)
    # Not employed       → 0   (likely actively looking)
    employment_score = 100.0 if is_employed == 1 else 0.0

    # ── Sub-score 3: Job stability (0–100) ──────────────────────────────────
    # 0 changes → 100 (very stable)
    # 1 change  → 80
    # 2 changes → 60
    # 3 changes → 40
    # 4+ changes → scales down to 0 at 8+
    stability_score = max(0.0, 100.0 - (job_changes * 20.0))

    # ── Sub-score 4: Seniority (0–100) ──────────────────────────────────────
    # Senior professionals are harder to headhunt but are high-value passive talent
    seniority_map = {
        "senior": 100.0,
        "mid":     60.0,
        "junior":  20.0,
    }
    seniority_score = seniority_map.get(seniority_level or "mid", 60.0)

    # ── Composite passivity score ────────────────────────────────────────────
    passivity = (
        0.35 * tenure_score
        + 0.30 * employment_score
        + 0.20 * stability_score
        + 0.15 * seniority_score
    )

    return round(min(100.0, max(0.0, passivity)), 2)


def get_passivity_label(score: float) -> str:
    """
    Human-readable label for the passivity score.
    Used in the UI transparency panel (REQ-PH-204).
    """
    if score >= 75:
        return "Highly passive"
    elif score >= 50:
        return "Moderately passive"
    elif score >= 25:
        return "Slightly passive"
    else:
        return "Likely active"
