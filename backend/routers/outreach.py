from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.models import Candidate, Job
from db.session import get_db
from services.ai.grok_services import generate_outreach_message

router = APIRouter()

@router.patch("/{job_id}/candidate/{candidate_id}/initiate")
def initiate_outreach(job_id: int, candidate_id: int, db: Session = Depends(get_db)):
    """
    Initiates outreach for a candidate.
    Uses Grok to generate a personalized outreach message.
    REQ-PH-401, REQ-PH-402 | PRED-04
    """
    c = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.job_id == job_id
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if c.shortlist_status != "approved":
        raise HTTPException(status_code=400, detail="Only approved candidates can be contacted")

    job = db.query(Job).filter(Job.id == job_id).first()

    # Generate personalized outreach message via Grok
    message = generate_outreach_message(
        candidate_name=c.name or f"Candidate {c.id}",
        current_title=c.current_title or "",
        current_company=c.current_company or "",
        skills=c.skills or "",
        job_title=job.title if job else "the position",
        job_description=job.description if job else "",
        passivity_score=c.passivity_score or 50,
        fit_score=c.fit_score or 0,
    )

    c.outreach_status = "initiated"
    db.commit()

    return {
        "message": "Outreach initiated",
        "candidate": c.name,
        "status": "initiated",
        "outreach_message": message,
    }


@router.patch("/{job_id}/initiate-all")
def initiate_outreach_all(job_id: int, db: Session = Depends(get_db)):
    """Initiate outreach for all approved candidates."""
    job = db.query(Job).filter(Job.id == job_id).first()
    candidates = db.query(Candidate).filter(
        Candidate.job_id == job_id,
        Candidate.shortlist_status == "approved",
        Candidate.outreach_status == "pending"
    ).all()

    results = []
    for c in candidates:
        message = generate_outreach_message(
            candidate_name=c.name or f"Candidate {c.id}",
            current_title=c.current_title or "",
            current_company=c.current_company or "",
            skills=c.skills or "",
            job_title=job.title if job else "the position",
            job_description=job.description if job else "",
            passivity_score=c.passivity_score or 50,
            fit_score=c.fit_score or 0,
        )
        c.outreach_status = "initiated"
        results.append({
            "candidate": c.name,
            "outreach_message": message,
        })

    db.commit()
    return {
        "message": f"Outreach initiated for {len(candidates)} candidates",
        "results": results,
    }
