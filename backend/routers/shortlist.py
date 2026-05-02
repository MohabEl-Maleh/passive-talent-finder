# backend/routers/shortlist.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.models import Candidate
from db.session import get_db

router = APIRouter()

@router.patch("/{job_id}/candidate/{candidate_id}")
def update_shortlist_status(
    job_id: int, candidate_id: int, status: str, db: Session = Depends(get_db)
):
    """Hiring Manager approves or rejects a candidate. Covers REQ-PH-305, PRED-03."""
    if status not in ("approved", "rejected", "pending", "shortlisted", "none"):
        raise HTTPException(status_code=400, detail="Invalid status")
    c = db.query(Candidate).filter(Candidate.id == candidate_id, Candidate.job_id == job_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    c.shortlist_status = status
    db.commit()
    return {"message": f"Candidate {candidate_id} marked as {status}"}

@router.get("/{job_id}")
def get_shortlist(job_id: int, db: Session = Depends(get_db)):
    """Returns all shortlisted candidates for a job."""
    import json
    candidates = db.query(Candidate).filter(
        Candidate.job_id == job_id,
        Candidate.shortlist_status != "pending"
    ).order_by(Candidate.composite_score.desc()).all()
    return [
        {
            "id": c.id, "name": c.name, "current_title": c.current_title,
            "composite_score": c.composite_score, "passivity_score": c.passivity_score,
            "fit_score": c.fit_score, "shortlist_status": c.shortlist_status,
            "outreach_status": c.outreach_status,
            "score_breakdown": json.loads(c.score_breakdown) if c.score_breakdown else {},
        }
        for c in candidates
    ]
