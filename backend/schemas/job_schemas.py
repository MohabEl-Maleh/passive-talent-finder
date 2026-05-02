from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class JobCreate(BaseModel):
    title: str
    description: str
    required_skills: str
    min_experience: int = 0
    industry: Optional[str] = None
    created_by: str = "recruiter"

class JobResponse(BaseModel):
    id: int
    title: str
    description: str
    required_skills: str
    min_experience: int
    industry: Optional[str]
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True