# backend/db/models.py
# SQLAlchemy database models.
# Each table maps to one core domain entity.

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import enum

Base = declarative_base()


class OutreachStatus(str, enum.Enum):
    pending = "pending"
    initiated = "initiated"


class ShortlistStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Job(Base):
    """A job posting created by the Hiring Manager or Recruiter."""
    __tablename__ = "jobs"

    id              = Column(Integer, primary_key=True, index=True)
    title           = Column(String, nullable=False)
    description     = Column(Text, nullable=False)         # Full job description text
    required_skills = Column(Text, nullable=False)         # Comma-separated skills
    min_experience  = Column(Integer, default=0)           # Years
    industry        = Column(String, nullable=True)
    # Ranking is based 100% on job-fit score.
    # Passivity score is stored and displayed separately as outreach context only.
    created_by      = Column(String, default="recruiter")  # "recruiter" or "hiring_manager"
    created_at      = Column(DateTime, default=datetime.utcnow)

    candidates      = relationship("Candidate", back_populates="job")


class Candidate(Base):
    """A parsed candidate extracted from an uploaded CV."""
    __tablename__ = "candidates"

    id               = Column(Integer, primary_key=True, index=True)
    job_id           = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    name             = Column(String, nullable=True)
    email            = Column(String, nullable=True)
    current_title    = Column(String, nullable=True)
    current_company  = Column(String, nullable=True)
    skills           = Column(Text, nullable=True)          # Comma-separated
    years_experience = Column(Float, default=0)
    tenure_months    = Column(Float, default=0)             # Time at current job
    is_employed      = Column(Integer, default=1)           # 1 = currently employed
    job_changes      = Column(Integer, default=0)           # Number of past jobs
    seniority_level  = Column(String, nullable=True)        # junior/mid/senior/lead
    raw_cv_text      = Column(Text, nullable=True)          # Full extracted text

    # AI scores (filled after matching run)
    passivity_score  = Column(Float, nullable=True)         # 0–100
    fit_score        = Column(Float, nullable=True)         # 0–100
    composite_score  = Column(Float, nullable=True)         # 0–100
    score_breakdown  = Column(Text, nullable=True)          # JSON string of SHAP/explanation

    # Status fields (REQ-PH-301 to 306)
    shortlist_status = Column(String, default="pending")    # pending/approved/rejected
    outreach_status  = Column(String, default="pending")    # pending/initiated

    cv_hash          = Column(String, nullable=True)           # MD5 of raw text for dedup
    source_file      = Column(String, nullable=True)           # Original filename
    uploaded_at      = Column(DateTime, default=datetime.utcnow)
    job              = relationship("Job", back_populates="candidates")


class CVDataset(Base):
    """Tracks every upload batch — supports fresh upload and append/update modes."""
    __tablename__ = "cv_datasets"

    id           = Column(Integer, primary_key=True, index=True)
    job_id       = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    upload_mode  = Column(String, nullable=False)   # "fresh" or "append"
    file_count   = Column(Integer, default=0)        # CVs in this batch
    added_count  = Column(Integer, default=0)        # New CVs added (after dedup)
    skipped_count= Column(Integer, default=0)        # Duplicates skipped
    uploaded_by  = Column(String, default="recruiter")
    uploaded_at  = Column(DateTime, default=datetime.utcnow)
