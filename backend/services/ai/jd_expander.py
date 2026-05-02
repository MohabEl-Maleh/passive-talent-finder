# backend/services/ai/jd_expander.py
#
# Grok-powered Job Description Expansion.
# Calls xAI Grok API once per job to enrich the JD with:
#   1. Synonym skill phrases candidates might use in CVs
#   2. Alternative job titles for the role
#   3. Related certifications and tools
#
# This bridges the vocabulary gap between JD language and CV language.
# Example: JD says "generate reports" → Grok adds "automated reporting
# workflows, dashboard creation, data visualization outputs"
#
# Falls back to rule-based enrichment if API key not set or call fails.
#
# Reference:
#   Rabczuk (2025). The Resume Parsing Crisis of 2025. SSRN 6061595.
#   — identifies vocabulary divergence as root cause of ATS failure.

import os
import json
import time
from functools import lru_cache


def expand_job_description(job_description: str) -> str:
    """
    Expand a job description using Grok LLM.
    Returns enriched JD string for use in embedding.
    Falls back to rule-based enrichment if Grok unavailable.
    """
    api_key = os.environ.get("GROQ_API_KEY", "")

    if not api_key:
        print("[Grok] GROQ_API_KEY not set — using rule-based enrichment.")
        return _rule_based_enrichment(job_description)

    try:
        import requests

        prompt = f"""You are an expert HR consultant and recruitment specialist.

Given this job description, generate additional context to help match it with candidate CVs.
Return ONLY a JSON object with these fields:
{{
  "skill_synonyms": ["list of 15 alternative phrases candidates use for the required skills"],
  "related_certifications": ["list of 8 relevant certifications or qualifications"],
  "alternative_titles": ["list of 5 alternative job titles for this role"],
  "key_activities": ["list of 10 key work activities described differently than in the JD"]
}}

Job Description:
{job_description[:1000]}

Return only valid JSON, no other text."""

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 600,
                "temperature": 0.3,
            },
            timeout=15,
        )

        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            # Strip markdown code blocks if present
            content = content.replace("```json", "").replace("```", "").strip()
            data = json.loads(content)

            expansions = []
            if data.get("skill_synonyms"):
                expansions.append("Related skills: " + ", ".join(data["skill_synonyms"]))
            if data.get("related_certifications"):
                expansions.append("Certifications: " + ", ".join(data["related_certifications"]))
            if data.get("alternative_titles"):
                expansions.append("Related roles: " + ", ".join(data["alternative_titles"]))
            if data.get("key_activities"):
                expansions.append("Key activities: " + ", ".join(data["key_activities"]))

            enriched = job_description + "\n\n" + "\n".join(expansions)
            print(f"[Grok] JD expanded successfully — {len(enriched)} chars")
            return enriched

        else:
            print(f"[Grok] API error {response.status_code} — falling back to rule-based.")
            return _rule_based_enrichment(job_description)

    except Exception as e:
        print(f"[Grok] Exception: {e} — falling back to rule-based.")
        return _rule_based_enrichment(job_description)


def _rule_based_enrichment(job_description: str) -> str:
    """Fallback enrichment using hardcoded domain synonyms."""
    jd_lower = job_description.lower()
    enrichments = []

    if any(w in jd_lower for w in ["data analyst", "data analysis", "analytics"]):
        enrichments.append("data analysis reporting dashboards insights metrics KPIs business intelligence automated reporting workflows")
    if any(w in jd_lower for w in ["python", "sql", "tableau", "power bi"]):
        enrichments.append("data visualization querying databases automation scripting ETL pipelines")
    if any(w in jd_lower for w in ["machine learning", "nlp", "ai", "deep learning"]):
        enrichments.append("model training neural networks classification prediction artificial intelligence NLP transformers")
    if any(w in jd_lower for w in ["contracts", "claims", "fidic", "eot"]):
        enrichments.append(
            "contract administration FIDIC EOT extension of time claims management variation orders "
            "subcontracts dispute resolution arbitration CLAC CICCM procurement tendering pre-award "
            "post-award contractual correspondence cost claims NEC JCT DAB prolongation"
        )
    if any(w in jd_lower for w in ["finance", "accounting", "financial"]):
        enrichments.append("financial reporting budgeting forecasting reconciliation ECL IFRS balance sheet")
    if any(w in jd_lower for w in ["software", "developer", "engineer", "backend", "frontend"]):
        enrichments.append("software development coding programming APIs microservices deployment CI/CD")
    if any(w in jd_lower for w in ["marketing", "sales", "growth"]):
        enrichments.append("campaigns customer acquisition revenue conversion funnel CRM optimization")

    if enrichments:
        return job_description + "\n\nRelated context: " + " ".join(enrichments)
    return job_description
