# backend/services/ai/fit_scorer.py
#
# Three-signal hybrid scoring pipeline:
#
# SIGNAL 1 — BM25 Sparse Retrieval (25% weight)
#   Exact keyword matching. Penalizes CVs missing required terms.
#   Solves the "Ahmed Saqer problem" — Sales Manager with zero FIDIC/EOT/CLAC
#   keywords scores near zero on BM25 regardless of semantic similarity.
#
# SIGNAL 2 — Qwen3-Embedding Semantic Similarity (45% weight)
#   Dense vector matching. Catches meaning-equivalent phrases.
#   CV preprocessed to remove noise sections before embedding.
#   JD expanded with domain synonyms before embedding.
#
# SIGNAL 3 — Keyword Match (30% weight)
#   Direct required-skills matching from the skills field.
#   Rewards exact skill matches with bonus scoring.
#
# STAGE 2 — Qwen3-Reranker (refinement on top 50 only)
#   Cross-encoder deep analysis of shortlisted candidates.
#
# References:
#   Robertson & Zaragoza (2009). BM25 and Beyond. Found. & Trends in IR.
#   Zhang et al. (2025). Qwen3 Embedding. arXiv:2506.05176.

import numpy as np
import re
from functools import lru_cache
from services.ai.bm25 import BM25
from services.ai.jd_expander import expand_job_description
from services.ai.skill_matcher import compute_skill_overlap_score

IRRELEVANCE_THRESHOLD = 30.0
RERANK_TOP_N          = 10

RELEVANT_SECTIONS = [
    "skills", "experience", "work experience", "employment", "technical skills",
    "professional experience", "education", "projects", "certifications",
    "summary", "profile", "objective", "qualifications", "expertise",
]

NOISE_SECTIONS = [
    "hobbies", "interests", "references", "volunteer", "sports",
    "awards", "publications", "activities",
]


def _preprocess_cv(cv_text: str, max_chars: int = 2000) -> str:
    if not cv_text:
        return ""
    # Strip personal info lines before embedding
    personal_patterns = [
        r'\b(nationality|marital|date of birth|military|religion|gender)\b',
        r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}',
        r'https?://',
        r'linkedin\.com',
        r'\+?\d[\d\s\-\.]{9,}',
    ]
    import re as _re
    clean_lines = []
    for line in cv_text.split("\n"):
        if not any(_re.search(p, line.lower()) for p in personal_patterns):
            clean_lines.append(line)
    cv_text = "\n".join(clean_lines)
    lines = cv_text.split("\n")
    result_lines = []
    skip_section = False
    current_section_lines = 0

    for line in lines:
        line_stripped = line.strip()
        line_lower = line_stripped.lower()
        is_header = (
            len(line_stripped) < 50 and
            (line_stripped.isupper() or line_stripped.istitle() or line_stripped.endswith(":"))
        )
        if is_header:
            if any(noise in line_lower for noise in NOISE_SECTIONS):
                skip_section = True
                continue
            elif any(rel in line_lower for rel in RELEVANT_SECTIONS):
                skip_section = False
                current_section_lines = 0
            else:
                skip_section = False
        if skip_section:
            continue
        if is_header:
            current_section_lines = 0
            result_lines.append(line_stripped)
        elif current_section_lines < 20 and line_stripped:
            result_lines.append(line_stripped)
            current_section_lines += 1

    processed = "\n".join(result_lines)
    if len(processed.strip()) < 100:
        processed = cv_text
    return processed[:max_chars]


def _enrich_job_description(job_description: str) -> str:
    jd_lower = job_description.lower()
    enrichments = []

    if any(w in jd_lower for w in ["data analyst", "data analysis", "analytics"]):
        enrichments.append("data analysis reporting dashboards insights metrics KPIs business intelligence automated")
    if any(w in jd_lower for w in ["python", "sql", "tableau", "power bi"]):
        enrichments.append("data visualization querying databases automation scripting")
    if any(w in jd_lower for w in ["machine learning", "nlp", "ai", "deep learning"]):
        enrichments.append("model training neural networks classification prediction artificial intelligence")
    if any(w in jd_lower for w in ["finance", "accounting", "financial"]):
        enrichments.append("financial reporting budgeting forecasting reconciliation ECL IFRS")
    if any(w in jd_lower for w in ["contracts", "claims", "fidic", "eot"]):
        enrichments.append(
            "contract administration FIDIC EOT extension of time claims management variation orders "
            "subcontracts dispute resolution arbitration CLAC CICCM procurement tendering pre-award "
            "post-award contractual correspondence cost claims NEC JCT"
        )
    if any(w in jd_lower for w in ["software", "developer", "engineer", "backend", "frontend"]):
        enrichments.append("software development coding programming APIs microservices deployment")
    if any(w in jd_lower for w in ["marketing", "sales", "growth"]):
        enrichments.append("campaigns customer acquisition revenue conversion funnel optimization")

    if enrichments:
        return job_description + "\n\nRelated context: " + " ".join(enrichments)
    return job_description


@lru_cache(maxsize=1)
def _get_embedding_model():
    from sentence_transformers import SentenceTransformer
    print("[AI] Loading all-mpnet-base-v2...")
    model = SentenceTransformer("all-mpnet-base-v2")
    print("[AI] all-mpnet-base-v2 loaded successfully.")
    return model, "minilm"


@lru_cache(maxsize=1)
def _get_reranker_model():
    # Reranker disabled — BM25 + skill overlap + Groq provide sufficient accuracy
    return None


def compute_fit_score(cv_text: str, job_description: str) -> float:
    if not cv_text.strip() or not job_description.strip():
        return 0.0
    enriched_jd  = expand_job_description(job_description)
    processed_cv = _preprocess_cv(cv_text)
    semantic     = _semantic_score(processed_cv, enriched_jd)
    keywords     = _extract_keywords(job_description)
    req_skills   = [s.strip() for s in job_description.split("Required skills:")[-1].split(",") if s.strip()] if "Required skills:" in job_description else []
    keyword      = _keyword_score(cv_text, keywords, req_skills)
    bm25_score   = _single_bm25_score(cv_text, job_description)
    skill_score  = compute_skill_overlap_score(cv_text, job_description)
    combined     = (0.40 * semantic) + (0.25 * keyword) + (0.20 * bm25_score) + (0.15 * skill_score)
    combined     = _apply_specificity_penalty(combined, cv_text, job_description)
    return round(float(np.clip(combined, 0.0, 100.0)), 2)


def compute_fit_score_with_reranker(cv_text: str, job_description: str, stage1_score: float) -> tuple:
    reranker = _get_reranker_model()
    if reranker is None:
        final_score = stage1_score
    else:
        try:
            enriched_jd  = expand_job_description(job_description)
            processed_cv = _preprocess_cv(cv_text, max_chars=600)
            rerank_score = reranker.predict([(enriched_jd[:512], processed_cv)])[0]
            normalized   = float(np.clip((rerank_score + 10) / 20 * 100, 0, 100))
            final_score  = round((0.4 * stage1_score) + (0.6 * normalized), 2)
        except Exception as e:
            print(f"[AI] Reranker error: {e}. Using stage 1 score.")
            final_score = stage1_score

    is_relevant    = final_score >= IRRELEVANCE_THRESHOLD
    relevance_note = (
        f"Candidate does not meet the minimum qualification threshold "
        f"(score: {final_score:.0f}/100). CV content does not sufficiently "
        f"match the required skills and job description."
    ) if not is_relevant else None

    return round(final_score, 2), is_relevant, relevance_note


def _apply_specificity_penalty(score: float, cv_text: str, job_description: str) -> float:
    """
    Apply a penalty if the JD contains specialized terms but the CV has none of them.
    Prevents estimation/sales engineers from ranking high on contracts roles.
    """
    jd_lower = job_description.lower()
    cv_lower  = cv_text.lower()

    # Define specialty term groups — if JD has any, CV must have at least some
    specialty_groups = [
        # Contracts/Claims
        ["fidic", "eot", "extension of time", "clac", "ciccm", "arbitration",
         "claims engineer", "contract administration", "dispute resolution", "dab"],
        # Data Science
        ["tensorflow", "pytorch", "neural network", "nlp", "deep learning",
         "machine learning model", "scikit", "pandas dataframe"],
        # Software Engineering
        ["microservices", "kubernetes", "docker", "ci/cd", "rest api",
         "backend", "frontend", "full stack"],
    ]

    for group in specialty_groups:
        jd_has_specialty  = sum(1 for t in group if t in jd_lower)
        cv_has_specialty  = sum(1 for t in group if t in cv_lower)

        # JD clearly requires this specialty (3+ terms) but CV has none
        if jd_has_specialty >= 3 and cv_has_specialty == 0:
            penalty = 0.70  # reduce score by 30%
            return round(score * penalty, 2)

        # JD clearly requires this specialty but CV has very little
        if jd_has_specialty >= 3 and cv_has_specialty == 1:
            penalty = 0.85  # reduce score by 15%
            return round(score * penalty, 2)

    return score


def batch_stage1_scores(cv_texts: list, job_description: str) -> list:
    if not cv_texts:
        return []

    enriched_jd   = expand_job_description(job_description)
    keywords      = _extract_keywords(job_description)
    processed_cvs = [_preprocess_cv(t) for t in cv_texts]

    # ── BM25 scores for ALL candidates ───────────────────────────────────────
    print("[AI] Computing BM25 sparse scores...")
    bm25 = BM25(cv_texts)  # use full CV text for BM25
    bm25_scores = bm25.get_all_scores(job_description)

    # ── Semantic scores via Qwen3-Embedding ───────────────────────────────────
    model, model_type = _get_embedding_model()
    print("[AI] Computing semantic embedding scores...")

    if model_type == "qwen3":
        jd_embedding = model.encode(enriched_jd[:800], normalize_embeddings=True, prompt_name="query")
    else:
        jd_embedding = model.encode(enriched_jd[:800], normalize_embeddings=True)

    cv_embeddings = model.encode(
        processed_cvs, normalize_embeddings=True, batch_size=16, show_progress_bar=False
    )

    scores = []
    for i, (cv_text, cv_emb) in enumerate(zip(cv_texts, cv_embeddings)):
        semantic = float(np.clip(
            ((float(np.dot(cv_emb, jd_embedding)) + 1) / 2) * 100, 0, 100
        ))
        req_skills = [s.strip() for s in job_description.split("Required skills:")[-1].split(",") if s.strip()] if "Required skills:" in job_description else []
        keyword  = _keyword_score(cv_text, keywords, req_skills)
        bm25_s   = bm25_scores[i]
        skill_s  = compute_skill_overlap_score(cv_text, job_description)
        combined = (0.40 * semantic) + (0.25 * keyword) + (0.20 * bm25_s) + (0.15 * skill_s)
        combined = _apply_specificity_penalty(combined, cv_text, job_description)
        scores.append(round(float(np.clip(combined, 0, 100)), 2))

    return scores


def _single_bm25_score(cv_text: str, job_description: str) -> float:
    """BM25 score for a single CV against JD."""
    bm25 = BM25([cv_text])
    scores = bm25.get_all_scores(job_description)
    return scores[0] if scores else 0.0


def _semantic_score(cv_text: str, job_description: str) -> float:
    model, model_type = _get_embedding_model()
    if model_type == "qwen3":
        embeddings = model.encode(
            [job_description[:800], cv_text[:2000]],
            normalize_embeddings=True, prompt_name="query",
        )
    else:
        embeddings = model.encode([job_description[:800], cv_text[:2000]], normalize_embeddings=True)
    similarity = float(np.dot(embeddings[0], embeddings[1]))
    return float(np.clip(((similarity + 1) / 2) * 100, 0.0, 100.0))


def _extract_keywords(job_description: str) -> list:
    text_lower = job_description.lower()
    keywords = []
    skills_match = re.search(r'required skills?[:\s]+([^\n\.]+)', text_lower)
    if skills_match:
        raw = skills_match.group(1)
        keywords = [k.strip() for k in re.split(r'[,;]', raw) if k.strip()]

    skill_indicators = {
        'python', 'java', 'javascript', 'typescript', 'react', 'node',
        'sql', 'mongodb', 'nlp', 'tensorflow', 'pytorch', 'sklearn',
        'scikit', 'pandas', 'numpy', 'keras', 'opencv', 'docker',
        'kubernetes', 'aws', 'azure', 'machine learning', 'deep learning',
        'accounting', 'finance', 'excel', 'sap', 'quickbooks', 'auditing',
        'tableau', 'powerbi', 'power bi', 'r', 'matlab', 'statistics',
        'data analysis', 'data visualization', 'business intelligence',
        'management', 'leadership', 'agile', 'scrum', 'git', 'linux',
        'html', 'css', 'php', 'ruby', 'swift', 'kotlin', 'flutter',
        'spark', 'hadoop', 'kafka', 'django', 'flask',
        # Construction/contracts specific
        'fidic', 'eot', 'clac', 'ciccm', 'claims', 'contracts',
        'arbitration', 'procurement', 'tendering', 'subcontract',
        'variation', 'dispute', 'pmp', 'oracle', 'civil engineering',
    }
    for word in skill_indicators:
        if word in text_lower and word not in keywords:
            keywords.append(word)
    return list(set(keywords))


def _keyword_score(cv_text: str, keywords: list, required_skills: list = None) -> float:
    """
    Score keyword match with 1.5x bonus for required skills.
    Skills explicitly listed in the Required Skills field are weighted
    higher than skills inferred from the JD body text.
    """
    if not keywords:
        return 50.0

    cv_lower = cv_text.lower()
    required_set = set(s.lower().strip() for s in (required_skills or []))

    total_weight = 0.0
    matched_weight = 0.0

    for kw in keywords:
        # Required skills get 1.5x weight, inferred skills get 1.0x
        weight = 1.5 if kw.lower() in required_set else 1.0
        total_weight += weight

        if kw in cv_lower:
            matched_weight += weight
        elif kw.replace('-', '') in cv_lower.replace('-', ''):
            matched_weight += weight * 0.5  # partial match

    if total_weight == 0:
        return 50.0

    return float(np.clip((matched_weight / total_weight) * 100, 0.0, 100.0))
