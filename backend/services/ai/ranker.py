# backend/services/ai/ranker.py
# Composite score and explanation builder.
# Ranking is 100% based on fit score.
# Passivity is informational only.

def compute_composite_score(fit_score: float) -> float:
    """Composite score = fit score only. Passivity does not affect ranking."""
    return round(float(fit_score), 2)


def build_explanation(
    passivity_score: float,
    fit_score: float,
    composite_score: float,
    tenure_months: float,
    is_employed: int,
    job_changes: int,
    seniority_level: str,
    is_relevant: bool = True,
    relevance_note: str = None,
) -> dict:
    """Build a full human-readable explanation for the candidate's scores."""

    # ── Fit explanation ───────────────────────────────────────────────────────
    if not is_relevant:
        fit_label = "Not Relevant"
        fit_explanation = relevance_note or "Candidate does not meet the minimum qualification threshold for this role."
        summary = f"⚠️ Not Relevant — {fit_explanation}"
        ranking_basis = "Candidate ranked low due to insufficient qualification match."
    elif fit_score >= 80:
        fit_label = "Excellent Match"
        fit_explanation = f"Strong match — {fit_score}/100 qualification match. CV content closely aligns with the job requirements and required skills."
        summary = f"Strong match — {fit_score:.1f}/100 qualification match."
        ranking_basis = "Ranked by job-fit score (semantic similarity + keyword match). Passivity score is informational only."
    elif fit_score >= 65:
        fit_label = "Good Match"
        fit_explanation = f"Good match — {fit_score}/100 qualification match. CV demonstrates relevant experience and most required skills."
        summary = f"Good match — {fit_score:.1f}/100 qualification match."
        ranking_basis = "Ranked by job-fit score (semantic similarity + keyword match). Passivity score is informational only."
    elif fit_score >= 45:
        fit_label = "Partial Match"
        fit_explanation = f"Partial match — {fit_score}/100 qualification match. Some relevant experience — may fit with additional context."
        summary = f"Partial match — {fit_score:.1f}/100 qualification match."
        ranking_basis = "Ranked by job-fit score. Passivity score is informational only."
    else:
        fit_label = "Weak Match"
        fit_explanation = f"Weak match — {fit_score}/100 qualification match. Limited alignment with the required skills and experience."
        summary = f"Weak match — {fit_score:.1f}/100 qualification match."
        ranking_basis = "Ranked by job-fit score. Passivity score is informational only."

    # ── Passivity explanation ─────────────────────────────────────────────────
    if passivity_score >= 67:
        passivity_label = "Highly passive"
        passivity_summary = "Proactive personalised outreach recommended."
    elif passivity_score >= 34:
        passivity_label = "Moderately passive"
        passivity_summary = "Candidate may already be open to opportunities."
    else:
        passivity_label = "Likely active"
        passivity_summary = "Candidate may already be job searching."

    passivity_factors = []

    if is_employed:
        passivity_factors.append({
            "factor": "Currently employed",
            "detail": "Candidate appears to be in an active role — typical passive talent profile.",
            "impact": "positive"
        })
    else:
        passivity_factors.append({
            "factor": "Not currently employed",
            "detail": "Candidate may already be actively searching for opportunities.",
            "impact": "negative"
        })

    if tenure_months >= 24:
        passivity_factors.append({
            "factor": f"Long tenure ({tenure_months/12:.1f} yrs)",
            "detail": "Extended time in current role suggests high stability and low likelihood of active search.",
            "impact": "positive"
        })
    elif tenure_months >= 12:
        passivity_factors.append({
            "factor": f"Moderate tenure ({tenure_months/12:.1f} yrs)",
            "detail": "Reasonable tenure — candidate is stable but not deeply entrenched.",
            "impact": "neutral"
        })
    else:
        passivity_factors.append({
            "factor": f"Short tenure ({tenure_months:.0f} months)",
            "detail": "Short time in current role — may be more open to change.",
            "impact": "negative"
        })

    if job_changes <= 1:
        passivity_factors.append({
            "factor": "High job stability",
            "detail": "Few job changes indicates a stable career — strong passive candidate signal.",
            "impact": "positive"
        })
    elif job_changes <= 3:
        passivity_factors.append({
            "factor": "Moderate job changes",
            "detail": f"{job_changes} role transitions — typical career progression.",
            "impact": "neutral"
        })
    else:
        passivity_factors.append({
            "factor": "Frequent job changes",
            "detail": f"{job_changes} role transitions suggests active career movement.",
            "impact": "negative"
        })

    return {
        "fit_score":              fit_score,
        "passivity_score":        passivity_score,
        "composite_score":        composite_score,
        "fit_label":              fit_label,
        "passivity_label":        passivity_label,
        "fit_explanation":        fit_explanation,
        "passivity_context_title":"Outreach Difficulty Indicator",
        "passivity_context_note": "Does not affect ranking. Helps you tailor your outreach strategy.",
        "passivity_factors":      passivity_factors,
        "passivity_summary":      passivity_summary,
        "summary":                summary,
        "ranking_basis":          ranking_basis,
        "is_relevant":            is_relevant,
        "relevance_note":         relevance_note,
    }
