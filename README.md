# Predictive AI for Headhunting: Identifying and Ranking Passive Talent

## Project Overview
This system identifies and ranks passive talent (currently employed professionals
not actively job-seeking) from uploaded CV datasets using a dual-score AI engine.

## Architecture — Domain-Driven Design
The project is structured as a modular HR platform domain. Each folder is a
self-contained domain that can be extended or merged with other HR modules
(e.g., onboarding, performance management) without touching existing code.

```
passive-talent-finder/
├── frontend/        → React + Tailwind (UI for Recruiter & Hiring Manager)
├── backend/         → FastAPI (REST API + business logic)
├── ml/              → ML training notebooks and scripts
└── docs/            → Architecture diagrams, API docs
```

## Two User Roles
- **Recruiter**: uploads CVs, defines job requirements, views ranked results, initiates outreach
- **Hiring Manager**: defines success criteria, approves/rejects shortlists, provides AI feedback

## AI Engine — Dual Score System
Every candidate gets two scores:
1. **Passivity Score (0–100)**: how unlikely they are to be actively job-hunting
2. **Job-Fit Score (0–100)**: semantic similarity to the job description
3. **Composite Score**: weighted combination (adjustable by recruiter)

## How to Run
See backend/README.md and frontend/README.md for setup instructions.

## Future Extension
To add a new HR module (e.g., Onboarding):
- Add `backend/routers/onboarding.py`
- Add `frontend/src/pages/onboarding/`
- Register the router in `backend/main.py`
Nothing else changes.
