from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import jobs, cvs, match, shortlist, outreach, files
from db.session import init_db

app = FastAPI(
    title="Passive Talent Finder API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()

app.include_router(jobs.router,      prefix="/api/jobs",      tags=["Jobs"])
app.include_router(cvs.router,       prefix="/api/cvs",       tags=["CVs"])
app.include_router(match.router,     prefix="/api/match",     tags=["Matching"])
app.include_router(shortlist.router, prefix="/api/shortlist", tags=["Shortlist"])
app.include_router(outreach.router,  prefix="/api/outreach",  tags=["Outreach"])
app.include_router(files.router,     prefix="/api/files",     tags=["Files"])

@app.get("/")
def root():
    return {"status": "Passive Talent Finder API is running"}
