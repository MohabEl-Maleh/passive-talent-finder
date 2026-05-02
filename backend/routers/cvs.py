from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import hashlib
import zipfile
import io
import os
import pandas as pd

from db.models import Candidate, CVDataset, Job
from db.session import get_db
from services.recruitment.cv_parser import parse_cv_file, parse_kaggle_csv_row

router = APIRouter()

CV_STORAGE = os.path.join(os.path.dirname(__file__), "..", "cv_storage")
os.makedirs(CV_STORAGE, exist_ok=True)


@router.post("/{job_id}/upload")
async def upload_cvs(
    job_id: int,
    upload_mode: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if upload_mode not in ("fresh", "append"):
        raise HTTPException(status_code=400, detail="upload_mode must be 'fresh' or 'append'")

    if upload_mode == "fresh":
        deleted = db.query(Candidate).filter(Candidate.job_id == job_id).delete()
        db.commit()
        print(f"[Upload] Fresh mode: deleted {deleted} existing candidates for job {job_id}")
        existing_hashes = set()
    else:
        existing_hashes = set(
            row[0] for row in
            db.query(Candidate.cv_hash).filter(Candidate.job_id == job_id).all()
            if row[0]
        )

    added = 0
    skipped = 0
    errors = 0

    for file in files:
        content = await file.read()
        print(f"[Upload] Processing: {file.filename} ({len(content)} bytes)")

        # ── CSV dataset (Kaggle-style) ────────────────────────────────────────
        if file.filename.lower().endswith(".csv"):
            try:
                df = pd.read_csv(io.BytesIO(content))
                for _, row in df.iterrows():
                    parsed = parse_kaggle_csv_row(row.to_dict())
                    if not parsed:
                        skipped += 1
                        continue
                    cv_hash = hashlib.md5(parsed.get("raw_cv_text", "").encode()).hexdigest()
                    if cv_hash in existing_hashes:
                        skipped += 1
                        continue
                    candidate = Candidate(job_id=job_id, **_to_fields(parsed, file.filename))
                    db.add(candidate)
                    existing_hashes.add(cv_hash)
                    added += 1
                db.commit()
                print(f"[Upload] CSV processed: {added} added so far")
                continue
            except Exception as e:
                print(f"[Upload] CSV processing failed: {e}")
                errors += 1
                continue

        # ── ZIP archive ───────────────────────────────────────────────────────
        if file.filename.lower().endswith(".zip"):
            print(f"[Upload] Extracting ZIP: {file.filename}")
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as zf:
                    entries = [e for e in zf.infolist() if not e.is_dir()]
                    print(f"[Upload] ZIP contains {len(entries)} files")
                    for entry in entries:
                        fname = entry.filename
                        ext = fname.lower().split(".")[-1]
                        if ext not in ("pdf", "docx", "txt"):
                            continue
                        base_name = fname.split("/")[-1].split("\\")[-1]
                        try:
                            file_content = zf.read(fname)
                            parsed = parse_cv_file(filename=base_name, file_bytes=file_content, existing_hashes=existing_hashes)
                            if not parsed:
                                skipped += 1
                                continue
                            candidate = Candidate(job_id=job_id, **_to_fields(parsed, base_name))
                            db.add(candidate)
                            db.flush()
                            safe_name = f"{candidate.id}_{base_name}"
                            with open(os.path.join(CV_STORAGE, safe_name), "wb") as f:
                                f.write(file_content)
                            candidate.source_file = safe_name
                            added += 1
                        except Exception as ze:
                            print(f"[Upload] ZIP entry error {fname}: {ze}")
                            errors += 1
                    db.commit()
            except zipfile.BadZipFile:
                print(f"[Upload] Invalid ZIP file: {file.filename}")
                errors += 1
            except Exception as e:
                print(f"[Upload] ZIP processing failed: {e}")
                errors += 1
            continue

        # ── Individual CV file (PDF, DOCX, TXT) ──────────────────────────────
        parsed = parse_cv_file(filename=file.filename, file_bytes=content, existing_hashes=existing_hashes)
        if not parsed:
            print(f"[Upload] Skipping {file.filename} — parsing returned None")
            skipped += 1
            continue

        candidate = Candidate(job_id=job_id, **_to_fields(parsed, file.filename))
        db.add(candidate)
        db.flush()

        safe_name = f"{candidate.id}_{file.filename}"
        with open(os.path.join(CV_STORAGE, safe_name), "wb") as f:
            f.write(content)
        candidate.source_file = safe_name
        added += 1

    db.add(CVDataset(
        job_id=job_id, upload_mode=upload_mode,
        file_count=len(files), added_count=added, skipped_count=skipped,
    ))
    db.commit()

    print(f"[Upload] Done: {added} added, {skipped} skipped, {errors} errors")
    return {
        "message": f"Upload complete ({upload_mode} mode)",
        "files_received": len(files),
        "candidates_added": added,
        "duplicates_skipped": skipped,
        "errors": errors,
    }


def _to_fields(parsed: dict, filename: str) -> dict:
    raw_text = parsed.get("raw_cv_text", "")
    return {
        "name":             parsed.get("name"),
        "email":            parsed.get("email"),
        "current_title":    parsed.get("current_title"),
        "current_company":  parsed.get("current_company"),
        "skills":           parsed.get("skills"),
        "years_experience": parsed.get("years_experience", 0),
        "tenure_months":    parsed.get("tenure_months", 0),
        "is_employed":      parsed.get("is_employed", 1),
        "job_changes":      parsed.get("job_changes", 0),
        "seniority_level":  parsed.get("seniority_level"),
        "raw_cv_text":      raw_text,
        "cv_hash":          hashlib.md5(raw_text.encode()).hexdigest(),
        "source_file":      filename,
    }


@router.get("/{job_id}/dataset-history")
def get_dataset_history(job_id: int, db: Session = Depends(get_db)):
    logs = db.query(CVDataset).filter(CVDataset.job_id == job_id).order_by(CVDataset.uploaded_at.desc()).all()
    return [
        {"batch_id": l.id, "upload_mode": l.upload_mode, "added": l.added_count,
         "skipped": l.skipped_count, "uploaded_at": l.uploaded_at}
        for l in logs
    ]


@router.get("/{job_id}/count")
def get_candidate_count(job_id: int, db: Session = Depends(get_db)):
    count = db.query(Candidate).filter(Candidate.job_id == job_id).count()
    return {"job_id": job_id, "total_candidates": count}
