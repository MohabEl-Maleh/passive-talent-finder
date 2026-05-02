# backend/services/ai/grok_services.py
#
# Groq-powered AI services (using Llama 3.3 70B via Groq API):
#
# 1. CV Field Extraction — DISABLED (using regex parser for reliability)
# 2. Candidate Summary, 3. Outreach, 4. JD Quality — all active
# 2. Candidate Summary — human-readable fit assessment
# 3. Outreach Message — personalized recruitment email
# 4. JD Quality Checker — analyses JD quality before matching
#
# All services fall back gracefully if GROQ_API_KEY is not set.

import os
import json
import requests
import time
from typing import Optional

XAI_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
GROK_MODEL   = "llama-3.3-70b-versatile"


def _call_grok(prompt: str, max_tokens: int = 800) -> Optional[str]:
    """Base function to call Groq API. Returns response text or None."""
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return None
    try:
        response = requests.post(
            XAI_BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROK_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.2,
            },
            timeout=15,
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        if response.status_code == 429:
            # Exponential backoff — wait longer each retry
            for wait in [5, 10, 20]:
                print(f"[Groq] Rate limit hit — waiting {wait} seconds...")
                time.sleep(wait)
                try:
                    retry = requests.post(
                        XAI_BASE_URL,
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        json={"model": GROK_MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens, "temperature": 0.2},
                        timeout=15,
                    )
                    if retry.status_code == 200:
                        return retry.json()["choices"][0]["message"]["content"]
                except:
                    pass
        print(f"[Groq] API error: {response.status_code}")
        return None
    except Exception as e:
        print(f"[Groq] Exception: {e}")
        return None


# ── Service 1: CV Field Extraction ───────────────────────────────────────────

def extract_cv_fields_with_grok(cv_text: str) -> Optional[dict]:
    """
    Use Groq to extract structured fields from raw CV text.
    Much more accurate than regex for names, titles, companies.
    """
    prompt = f"""You are an expert CV parser. Extract structured information from this CV text.
Return ONLY a valid JSON object with these exact fields:
{{
  "name": "Full name of the candidate",
  "email": "email address or null",
  "current_title": "Most recent job title or null",
  "current_company": "Most recent employer name or null",
  "skills": "Comma-separated list of up to 8 most relevant technical skills and certifications",
  "years_experience": 0,
  "seniority_level": "junior or mid or senior"
}}

Rules:
- years_experience: integer, TOTAL years of professional experience across ALL jobs combined. Find the earliest job start year in the CV, subtract from 2025. If someone started working in 2019, years_experience = 6.
- seniority_level: "senior" if 8+ years OR title contains senior/lead/director/principal/manager. "junior" if less than 2 years OR intern/graduate/trainee. Otherwise "mid".
- skills: extract the most relevant technical skills, certifications (CLAC, FIDIC, PMP etc), and tools. Do NOT include soft skills like communication or leadership.
- Return ONLY the JSON, no markdown, no other text.

CV Text:
{cv_text[:2500]}"""

    result = _call_grok(prompt, max_tokens=300)
    if not result:
        return None

    try:
        result = result.replace("```json", "").replace("```", "").strip()
        data = json.loads(result)
        print(f"[Groq] CV parsed: {data.get('name', 'Unknown')} — {data.get('current_title', 'N/A')} — {data.get('years_experience', 0)}y")
        return data
    except Exception as e:
        print(f"[Groq] CV parse JSON error: {e}")
        return None


# ── Service 2: Candidate Summary ──────────────────────────────────────────────

def generate_candidate_summary(
    candidate_name: str,
    fit_score: float,
    passivity_score: float,
    current_title: str,
    skills: str,
    job_title: str,
    job_required_skills: str,
    score_breakdown: dict,
) -> str:
    """Generate a 2-3 sentence professional assessment of a candidate."""
    prompt = f"""You are a senior recruitment consultant writing a brief candidate assessment.

Candidate: {candidate_name}
Current Role: {current_title or 'Unknown'}
Skills: {skills or 'Not specified'}
Job Applied For: {job_title}
Required Skills: {job_required_skills}
Job-Fit Score: {fit_score:.0f}/100

Write 2-3 sentences covering:
1. How well they match the role and why
2. One specific strength from their profile
3. A brief outreach recommendation

Be direct and professional. No bullet points. Plain paragraph only."""

    result = _call_grok(prompt, max_tokens=200)
    if result:
        print(f"[Groq] Summary generated for {candidate_name}")
        return result.strip()

    # Fallback
    if fit_score >= 75:
        fit_label = "strong match"
    elif fit_score >= 55:
        fit_label = "good match"
    elif fit_score >= 35:
        fit_label = "partial match"
    else:
        fit_label = "weak match"

    return f"{candidate_name} is a {fit_label} for this role with a qualification score of {fit_score:.0f}/100."


# ── Service 3: Outreach Message ───────────────────────────────────────────────

def generate_outreach_message(
    candidate_name: str,
    current_title: str,
    current_company: str,
    skills: str,
    job_title: str,
    job_description: str,
    passivity_score: float,
    fit_score: float,
) -> str:
    """Generate a personalized outreach email for a shortlisted candidate."""
    prompt = f"""You are an expert headhunter writing a personalized outreach email.

Candidate: {candidate_name}
Current Role: {current_title or 'Professional'}
Current Company: {current_company or 'their current employer'}
Key Skills: {skills or 'relevant skills'}
Job-Fit Score: {fit_score:.0f}/100
Target Role: {job_title}
Role Summary: {job_description[:300]}

Write a short personalized outreach email (150-200 words) that:
1. Opens with a specific reference to their background
2. Briefly explains why this role is a strong fit for THEM
3. Creates curiosity without giving everything away
4. Has a clear but low-pressure call to action
5. Feels human, not like an AI template

Format:
Subject: [subject line]

[email body]

Sign off as: The Recruitment Team"""

    result = _call_grok(prompt, max_tokens=400)
    if result:
        print(f"[Groq] Outreach message generated for {candidate_name}")
        return result.strip()

    return f"""Subject: Exciting {job_title} Opportunity — {candidate_name}

Dear {candidate_name},

I came across your profile and was impressed by your experience as {current_title or 'a professional'} and your expertise in {skills[:80] if skills else 'your field'}.

We have an exciting {job_title} opportunity that aligns closely with your background. Given your skills and experience, I believe this could be a great next step in your career.

Would you be open to a brief conversation this week?

Best regards,
The Recruitment Team"""


# ── Service 4: JD Quality Checker ────────────────────────────────────────────

def check_jd_quality(job_title: str, job_description: str, required_skills: str) -> dict:
    """Analyse job description quality before running AI matching."""
    prompt = f"""You are an expert recruiter reviewing a job description for AI candidate matching quality.

Job Title: {job_title}
Required Skills: {required_skills}
Job Description: {job_description[:800]}

Return ONLY a valid JSON object:
{{
  "quality_score": 0,
  "issues": ["list of specific issues"],
  "suggestions": ["list of specific improvements"],
  "missing_elements": ["list of missing elements"],
  "verdict": "Excellent or Good or Needs Improvement or Poor"
}}

Return ONLY the JSON, no other text."""

    result = _call_grok(prompt, max_tokens=400)
    if result:
        try:
            cleaned = result.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)
            print(f"[Groq] JD quality: {data.get('verdict')} ({data.get('quality_score')}/100)")
            return data
        except Exception as e:
            print(f"[Groq] JD quality JSON error: {e}")

    # Fallback
    issues = []
    suggestions = []
    score = 100

    if len(job_description.split()) < 30:
        issues.append("Job description is too short")
        suggestions.append("Add at least 3-4 sentences describing responsibilities")
        score -= 30

    if len(required_skills.split(",")) < 3:
        issues.append("Too few required skills specified")
        suggestions.append("Add at least 5 specific technical skills")
        score -= 20

    if not any(w in job_description.lower() for w in ["year", "experience", "background"]):
        issues.append("Experience level not specified")
        suggestions.append("Add minimum years of experience required")
        score -= 15

    verdict = "Excellent" if score >= 85 else "Good" if score >= 65 else "Needs Improvement" if score >= 40 else "Poor"

    return {
        "quality_score": max(0, score),
        "issues": issues,
        "suggestions": suggestions,
        "missing_elements": [],
        "verdict": verdict,
    }
