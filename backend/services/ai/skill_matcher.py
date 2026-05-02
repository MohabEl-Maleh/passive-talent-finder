# backend/services/ai/skill_matcher.py
#
# Dynamic skill overlap scoring powered by Groq (Llama 3.3 70B).
# Instead of a hardcoded synonym dictionary, Groq generates skill
# synonym groups for ANY job description automatically.
#
# This makes the system flexible across all industries and roles:
# - Contracts Engineering: FIDIC ≈ EOT ≈ CLAC ≈ arbitration
# - Data Science: ML ≈ machine learning ≈ AI ≈ deep learning
# - Accounting: IFRS ≈ financial reporting ≈ balance sheet
# - Any other role: Groq handles it dynamically
#
# Falls back to hardcoded groups if Groq unavailable.
#
# References:
#   Rabczuk (2025). Resume Parsing Crisis. SSRN 6061595.
#   Channabasamma et al. (2021). NLP Resume Analytics Using SpaCy.

import os
import json
import re
from functools import lru_cache
from typing import List, Set


# ── Hardcoded fallback synonym groups ─────────────────────────────────────────
FALLBACK_SYNONYMS = [
    {"fidic", "fidic contract", "fidic red book", "fidic yellow book", "fidic silver book"},
    {"eot", "extension of time", "time extension", "prolongation"},
    {"clac", "clac certified", "clac certification"},
    {"ciccm", "ciccm certified"},
    {"arbitration", "dispute arbitration", "dispute resolution", "adr"},
    {"claims management", "claims engineer", "cost claims", "construction claims"},
    {"contract administration", "contract management", "contracts engineer"},
    {"variation orders", "variation order", "variations", "change orders"},
    {"subcontract", "subcontracts", "subcontractor management"},
    {"tendering", "tender", "pre-award", "procurement"},
    {"power bi", "powerbi", "power-bi", "microsoft power bi"},
    {"tableau", "tableau desktop", "tableau server"},
    {"sql", "mysql", "postgresql", "t-sql", "pl/sql"},
    {"python", "python programming", "python scripting"},
    {"machine learning", "ml", "deep learning", "ai", "artificial intelligence"},
    {"data analysis", "data analytics", "data analyst", "data science"},
    {"excel", "microsoft excel", "ms excel", "advanced excel"},
    {"civil engineering", "civil engineer", "structural engineering"},
    {"project management", "pmp", "prince2", "project manager"},
    {"sap", "sap erp", "sap s4hana"},
]


def _get_groq_skill_synonyms(job_description: str) -> List[List[str]]:
    """
    Ask Groq to generate skill synonym groups for this specific job.
    Returns list of synonym groups, each group is a list of equivalent terms.
    """
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return []

    try:
        import requests

        prompt = f"""You are an expert recruiter and NLP specialist.

For this job description, generate skill synonym groups — sets of terms that mean the same thing 
but candidates might write differently in their CVs.

Job Description:
{job_description[:600]}

Return ONLY a valid JSON array of arrays. Each inner array contains equivalent terms:
[
  ["term1", "synonym1", "synonym2"],
  ["term2", "synonym3", "synonym4"],
  ...
]

Rules:
- Generate 15-20 synonym groups
- Focus on technical skills, certifications, tools, and role-specific terminology
- Include abbreviations and full forms (e.g., ["eot", "extension of time", "prolongation"])
- Include tool variations (e.g., ["power bi", "powerbi", "microsoft power bi"])
- Be specific to this job's industry and requirements
- Return ONLY the JSON array, no other text"""

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 800,
                "temperature": 0.2,
            },
            timeout=15,
        )

        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            content = content.replace("```json", "").replace("```", "").strip()
            groups = json.loads(content)
            if isinstance(groups, list):
                # Convert to sets of lowercase strings
                result = []
                for group in groups:
                    if isinstance(group, list) and len(group) >= 2:
                        result.append([t.lower().strip() for t in group if t])
                print(f"[Groq] Generated {len(result)} skill synonym groups")
                return result

    except Exception as e:
        print(f"[Groq] Skill synonym generation failed: {e}")

    return []


# Cache synonyms per job description to avoid repeated API calls
@lru_cache(maxsize=20)
def _get_cached_synonyms(job_description_key: str) -> str:
    """Cache Groq synonym results as JSON string."""
    groups = _get_groq_skill_synonyms(job_description_key)
    return json.dumps(groups)


def _get_synonym_groups(job_description: str) -> List[List[str]]:
    """
    Get skill synonym groups for this job.
    Uses Groq if available, falls back to hardcoded groups.
    Combines both for maximum coverage.
    """
    # Use first 400 chars as cache key (captures the essence of the JD)
    cache_key = job_description[:400].strip()

    groq_groups = json.loads(_get_cached_synonyms(cache_key))

    # Combine Groq groups with fallback groups
    all_groups = groq_groups if groq_groups else []

    # Always add fallback groups as extra coverage
    fallback_as_lists = [list(g) for g in FALLBACK_SYNONYMS]
    all_groups = all_groups + fallback_as_lists

    return all_groups


def compute_skill_overlap_score(cv_text: str, jd_text: str) -> float:
    """
    Score 0-100 based on skill overlap between CV and JD.
    Uses Groq-generated synonym groups so equivalent terms match.
    """
    cv_lower  = cv_text.lower()
    jd_lower  = jd_text.lower()

    synonym_groups = _get_synonym_groups(jd_text)

    # Find which groups are relevant to the JD
    jd_relevant_groups = []
    for group in synonym_groups:
        if any(term in jd_lower for term in group):
            jd_relevant_groups.append(group)

    if not jd_relevant_groups:
        return 50.0  # neutral if no relevant skills found

    # Count how many JD-relevant groups are matched in CV
    matched = 0
    for group in jd_relevant_groups:
        if any(term in cv_lower for term in group):
            matched += 1

    score = (matched / len(jd_relevant_groups)) * 100
    return round(min(100.0, score), 2)


def extract_skills_from_text(text: str) -> List[str]:
    """Extract canonical skill names found in text."""
    text_lower = text.lower()
    found = []
    for group in FALLBACK_SYNONYMS:
        for synonym in group:
            if synonym in text_lower:
                canonical = min(group, key=len)
                if canonical not in found:
                    found.append(canonical)
                break
    return found
