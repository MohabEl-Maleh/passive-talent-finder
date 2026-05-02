from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db.models import Job, Candidate
from db.session import get_db
from services.ai.passivity_scorer import compute_passivity_score
from services.ai.fit_scorer import batch_stage1_scores, compute_fit_score_with_reranker, RERANK_TOP_N
from services.ai.ranker import compute_composite_score, build_explanation
import json

router = APIRouter()


@router.post("/{job_id}")
def run_matching(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    candidates = db.query(Candidate).filter(Candidate.job_id == job_id).all()
    if not candidates:
        raise HTTPException(status_code=400, detail="No CVs uploaded for this job yet")

    job_description = f"{job.title}. Required skills: {job.required_skills}. {job.description or ''}"

    # ── Stage 1: Batch scoring ────────────────────────────────────────────────
    print(f"[AI] Stage 1: Scoring {len(candidates)} candidates...")
    cv_texts = [c.raw_cv_text or "" for c in candidates]
    stage1_scores = batch_stage1_scores(cv_texts, job_description)

    for candidate, score in zip(candidates, stage1_scores):
        candidate.fit_score = score

    sorted_by_stage1 = sorted(
        zip(candidates, stage1_scores), key=lambda x: x[1], reverse=True
    )
    top_candidates  = [c for c, _ in sorted_by_stage1[:RERANK_TOP_N]]
    rest_candidates = [c for c, _ in sorted_by_stage1[RERANK_TOP_N:]]

    # ── Stage 2: Rerank top candidates ───────────────────────────────────────
    print(f"[AI] Stage 2: Reranking top {len(top_candidates)} candidates...")
    for candidate in top_candidates:
        final_score, is_relevant, relevance_note = compute_fit_score_with_reranker(
            cv_text=candidate.raw_cv_text or "",
            job_description=job_description,
            stage1_score=candidate.fit_score,
        )
        candidate.fit_score = final_score

        passivity = compute_passivity_score(
            tenure_months=candidate.tenure_months or 0,
            is_employed=candidate.is_employed or 1,
            job_changes=candidate.job_changes or 0,
            seniority_level=candidate.seniority_level,
        )
        composite   = compute_composite_score(fit_score=final_score)
        explanation = build_explanation(
            passivity_score=passivity,
            fit_score=final_score,
            composite_score=composite,
            tenure_months=candidate.tenure_months or 0,
            is_employed=candidate.is_employed or 1,
            job_changes=candidate.job_changes or 0,
            seniority_level=candidate.seniority_level,
            is_relevant=is_relevant,
            relevance_note=relevance_note,
        )

        # Try Groq summary — skip silently if rate limited
        try:
            from services.ai.grok_services import generate_candidate_summary
            import time
            rank = top_candidates.index(candidate)
            if rank < 3:
                time.sleep(8)
                summary = generate_candidate_summary(
                    candidate_name=candidate.name or f"Candidate {candidate.id}",
                    fit_score=final_score,
                    passivity_score=passivity,
                    current_title=candidate.current_title or "",
                    skills=candidate.skills or "",
                    job_title=job.title,
                    job_required_skills=job.required_skills,
                    score_breakdown=explanation,
                )
                if summary:
                    explanation["summary"] = summary
        except Exception:
            pass

        candidate.passivity_score  = passivity
        candidate.composite_score  = composite
        candidate.score_breakdown  = json.dumps(explanation)

    # ── Remaining candidates ──────────────────────────────────────────────────
    for candidate in rest_candidates:
        score        = candidate.fit_score
        is_relevant  = score >= 30.0
        relevance_note = (
            f"Candidate does not meet the minimum qualification threshold "
            f"(score: {score:.0f}/100)." if not is_relevant else None
        )
        passivity   = compute_passivity_score(
            tenure_months=candidate.tenure_months or 0,
            is_employed=candidate.is_employed or 1,
            job_changes=candidate.job_changes or 0,
            seniority_level=candidate.seniority_level,
        )
        composite   = compute_composite_score(fit_score=score)
        explanation = build_explanation(
            passivity_score=passivity,
            fit_score=score,
            composite_score=composite,
            tenure_months=candidate.tenure_months or 0,
            is_employed=candidate.is_employed or 1,
            job_changes=candidate.job_changes or 0,
            seniority_level=candidate.seniority_level,
            is_relevant=is_relevant,
            relevance_note=relevance_note,
        )
        candidate.passivity_score  = passivity
        candidate.composite_score  = composite
        candidate.score_breakdown  = json.dumps(explanation)

    db.commit()
    print(f"[AI] Matching complete. {len(candidates)} candidates scored.")
    return {"message": "AI matching complete", "candidates_scored": len(candidates)}


@router.get("/{job_id}/results")
def get_results(
    job_id: int,
    db: Session = Depends(get_db),
    skill_filter: str = Query(None),
    seniority: str = Query(None),
    limit: int = Query(50),
    show_irrelevant: bool = Query(False),
):
    query = db.query(Candidate).filter(
        Candidate.job_id == job_id,
        Candidate.composite_score.isnot(None)
    )
    if skill_filter:
        query = query.filter(Candidate.skills.ilike(f"%{skill_filter}%"))
    if seniority:
        query = query.filter(Candidate.seniority_level == seniority)

    candidates = query.order_by(Candidate.composite_score.desc()).limit(limit).all()

    results = []
    for c in candidates:
        breakdown  = json.loads(c.score_breakdown) if c.score_breakdown else {}
        is_relevant = breakdown.get("is_relevant", True)
        if not is_relevant and not show_irrelevant:
            continue
        results.append({
            "id":               c.id,
            "name":             c.name,
            "current_title":    c.current_title,
            "current_company":  c.current_company,
            "skills":           c.skills,
            "seniority_level":  c.seniority_level,
            "years_experience": c.years_experience,
            "passivity_score":  round(c.passivity_score or 0, 1),
            "fit_score":        round(c.fit_score or 0, 1),
            "composite_score":  round(c.composite_score or 0, 1),
            "score_breakdown":  breakdown,
            "shortlist_status": c.shortlist_status,
            "outreach_status":  c.outreach_status,
            "source_file":      c.source_file,
            "is_relevant":      is_relevant,
        })
    return results
