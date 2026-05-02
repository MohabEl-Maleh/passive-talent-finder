from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from db.models import Candidate
from db.session import get_db
import os

router = APIRouter()
CV_STORAGE = os.path.join(os.path.dirname(__file__), "..", "cv_storage")

@router.get("/{candidate_id}")
def get_cv_file(candidate_id: int, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not candidate.source_file:
        raise HTTPException(status_code=404, detail="No file stored for this candidate")

    # source_file is stored as "{id}_{filename}" already
    file_path = os.path.join(CV_STORAGE, candidate.source_file)

    # Fallback: try without prefix
    if not os.path.exists(file_path):
        base = candidate.source_file.split("_", 1)[-1] if "_" in candidate.source_file else candidate.source_file
        file_path = os.path.join(CV_STORAGE, base)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="CV file not found on server")

    ext = candidate.source_file.lower().split(".")[-1]
    media_types = {
        "pdf":  "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt":  "text/plain",
    }
    return FileResponse(
        path=file_path,
        media_type=media_types.get(ext, "application/octet-stream"),
        filename=base if not os.path.exists(os.path.join(CV_STORAGE, candidate.source_file)) else candidate.source_file,
    )
