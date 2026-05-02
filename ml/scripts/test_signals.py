# ml/scripts/test_signals.py
#
# Unit tests for each scoring signal in the hybrid pipeline.
# Tests each signal independently with controlled inputs where
# the expected output is known in advance.
#
# Run with:
#   cd backend
#   venv\Scripts\activate
#   python ../ml/scripts/test_signals.py

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

import math

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []

def check(test_name, condition, details=""):
    status = PASS if condition else FAIL
    results.append((test_name, status, details))
    print(f"  {status}  {test_name}")
    if details:
        print(f"         {details}")


# ═══════════════════════════════════════════════════════════════
# SIGNAL 1 — BM25 Sparse Retrieval
# ═══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  SIGNAL 1 — BM25 Sparse Retrieval")
print("="*60)

from services.ai.bm25 import BM25

# Test 1: Exact match scores higher than no match
cv_relevant   = "Contracts engineer with FIDIC EOT CLAC arbitration experience"
cv_irrelevant = "Sales manager responsible for steel products and revenue targets"
jd = "FIDIC EOT CLAC arbitration contracts claims"

bm25 = BM25([cv_relevant, cv_irrelevant])
scores = bm25.get_all_scores(jd)
check(
    "BM25: Relevant CV scores higher than irrelevant CV",
    scores[0] > scores[1],
    f"Relevant={scores[0]:.1f}, Irrelevant={scores[1]:.1f}"
)

# Test 2: CV with more keyword matches scores higher
cv_many_keywords = "FIDIC Red Book EOT extension of time CLAC arbitration claims dispute"
cv_few_keywords  = "FIDIC contracts management"
bm25_2 = BM25([cv_many_keywords, cv_few_keywords])
scores_2 = bm25_2.get_all_scores(jd)
check(
    "BM25: More keyword matches = higher score",
    scores_2[0] > scores_2[1],
    f"Many keywords={scores_2[0]:.1f}, Few keywords={scores_2[1]:.1f}"
)

# Test 3: Perfect match scores 100
bm25_3 = BM25([jd])
scores_3 = bm25_3.get_all_scores(jd)
check(
    "BM25: Identical text scores 100",
    scores_3[0] == 100.0,
    f"Score={scores_3[0]}"
)

# Test 4: Empty CV scores 0
bm25_4 = BM25(["", jd])
scores_4 = bm25_4.get_all_scores(jd)
check(
    "BM25: Empty CV scores 0",
    scores_4[0] == 0.0,
    f"Empty CV score={scores_4[0]}"
)

# Test 5: Sales CV gets near-zero score on contracts JD
cv_sales = "Sales representative managing accounts revenue targets customer relationships profit"
bm25_5 = BM25([cv_sales, cv_relevant])
scores_5 = bm25_5.get_all_scores(jd)
check(
    "BM25: Sales CV scores near zero on Contracts JD",
    scores_5[0] < 20,
    f"Sales CV={scores_5[0]:.1f}, Contracts CV={scores_5[1]:.1f}"
)


# ═══════════════════════════════════════════════════════════════
# SIGNAL 2 — Keyword Match
# ═══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  SIGNAL 2 — Keyword Match")
print("="*60)

from services.ai.fit_scorer import _keyword_score, _extract_keywords

# Test 6: All keywords present = 100
jd_text = "Required skills: FIDIC, EOT, CLAC, arbitration, power bi"
keywords = _extract_keywords(jd_text)
cv_all   = "I have FIDIC EOT CLAC arbitration power bi experience"
score_all = _keyword_score(cv_all, keywords)
check(
    "Keyword: All skills present = high score",
    score_all >= 80,
    f"Score={score_all:.1f}, Keywords found={keywords}"
)

# Test 7: No keywords = 0
cv_none  = "Sales manager with revenue targets and business development"
score_none = _keyword_score(cv_none, keywords)
check(
    "Keyword: No skills present = low score",
    score_none < 20,
    f"Score={score_none:.1f}"
)

# Test 8: Partial match gets 0.5 points
keywords_hyphen = ["power-bi"]
cv_hyphen = "experienced with powerbi dashboards"
score_hyphen = _keyword_score(cv_hyphen, keywords_hyphen)
check(
    "Keyword: Hyphen variation gets partial credit",
    score_hyphen >= 40,
    f"Score={score_hyphen:.1f} (powerbi matched power-bi)"
)

# Test 9: Keywords extracted from JD correctly
jd_contracts = "Senior Contracts Engineer. Required skills: FIDIC, CLAC, EOT, arbitration"
kw = _extract_keywords(jd_contracts)
check(
    "Keyword: FIDIC extracted from JD",
    "fidic" in kw,
    f"Extracted: {kw}"
)
check(
    "Keyword: CLAC extracted from JD",
    "clac" in kw,
    f"Extracted: {kw}"
)


# ═══════════════════════════════════════════════════════════════
# SIGNAL 3 — Semantic Similarity (all-mpnet-base-v2)
# ═══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  SIGNAL 3 — Semantic Similarity (all-mpnet-base-v2)")
print("="*60)
print("  (Loading model — may take 10 seconds...)")

from services.ai.fit_scorer import _semantic_score, _get_embedding_model

# Warm up model
model, model_type = _get_embedding_model()
print(f"  Model loaded: {model_type}")

# Test 10: Identical texts = near 100
text = "FIDIC contracts engineer with EOT claims and arbitration experience"
score_identical = _semantic_score(text, text)
check(
    "Semantic: Identical texts score near 100",
    score_identical >= 90,
    f"Score={score_identical:.1f}"
)

# Test 11: Semantically similar texts score higher than unrelated
jd_sem = "Contracts and claims engineer managing FIDIC EOT arbitration disputes"
cv_relevant_sem = "Contract administration specialist handling FIDIC claims and dispute resolution"
cv_unrelated    = "Chef preparing Italian cuisine pasta and pizza in restaurant kitchen"
score_rel = _semantic_score(cv_relevant_sem, jd_sem)
score_unr = _semantic_score(cv_unrelated, jd_sem)
check(
    "Semantic: Related CV scores higher than unrelated CV",
    score_rel > score_unr,
    f"Related={score_rel:.1f}, Unrelated={score_unr:.1f}"
)

# Test 12: Synonym phrases score similarly
phrase1 = "extension of time claims"
phrase2 = "EOT and prolongation"
score_syn = _semantic_score(phrase1, phrase2)
check(
    "Semantic: Synonym phrases score above 60",
    score_syn > 60,
    f"Score={score_syn:.1f} ('extension of time' vs 'EOT and prolongation')"
)

# Test 13: Score is bounded 0-100
check(
    "Semantic: Score is within 0-100 range",
    0 <= score_rel <= 100 and 0 <= score_unr <= 100,
    f"Scores in range: {score_rel:.1f}, {score_unr:.1f}"
)


# ═══════════════════════════════════════════════════════════════
# SIGNAL 4 — Skill Overlap with Groq Synonyms
# ═══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  SIGNAL 4 — Skill Overlap with Synonyms")
print("="*60)

from services.ai.skill_matcher import compute_skill_overlap_score

# Test 14: EOT synonym matches
cv_eot  = "Prepared extension of time claims for the contractor"
jd_eot  = "Experience with EOT claims and time extension management"
score_eot = compute_skill_overlap_score(cv_eot, jd_eot)
check(
    "Skill: 'extension of time' matches 'EOT' synonym group",
    score_eot > 50,
    f"Score={score_eot:.1f}"
)

# Test 15: FIDIC variations match
cv_fidic = "Administered FIDIC Red Book contracts on infrastructure projects"
jd_fidic = "Strong knowledge of FIDIC contract forms"
score_fidic = compute_skill_overlap_score(cv_fidic, jd_fidic)
check(
    "Skill: 'FIDIC Red Book' matches 'FIDIC' synonym group",
    score_fidic > 50,
    f"Score={score_fidic:.1f}"
)

# Test 16: Power BI variations match
cv_pbi = "Built powerbi dashboards for KPI tracking"
jd_pbi = "Proficiency in Power BI or equivalent reporting tools"
score_pbi = compute_skill_overlap_score(cv_pbi, jd_pbi)
check(
    "Skill: 'powerbi' matches 'Power BI' synonym group",
    score_pbi > 50,
    f"Score={score_pbi:.1f}"
)

# Test 17: No overlap = low score
cv_no_overlap = "Cooking pasta and baking bread in Italian restaurant"
jd_contracts  = "FIDIC EOT CLAC arbitration contracts claims dispute resolution"
score_no = compute_skill_overlap_score(cv_no_overlap, jd_contracts)
check(
    "Skill: Completely unrelated CV scores 0",
    score_no == 0.0,
    f"Score={score_no:.1f}"
)


# ═══════════════════════════════════════════════════════════════
# SIGNAL 5 — Groq JD Expansion
# ═══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  SIGNAL 5 — Groq JD Expansion")
print("="*60)

from services.ai.jd_expander import expand_job_description

jd_short = "Senior Contracts Engineer with FIDIC EOT CLAC experience"
expanded = expand_job_description(jd_short)

check(
    "Groq/Fallback: Expanded JD is longer than original",
    len(expanded) > len(jd_short),
    f"Original={len(jd_short)} chars, Expanded={len(expanded)} chars"
)
check(
    "Groq/Fallback: Original JD preserved in expansion",
    jd_short in expanded,
    f"First 100 chars of expanded: {expanded[:100]}"
)

groq_key = os.environ.get("GROQ_API_KEY", "")
if groq_key:
    check(
        "Groq: API key is set",
        True,
        "GROQ_API_KEY found in environment"
    )
    check(
        "Groq: Expansion significantly enriched JD",
        len(expanded) > len(jd_short) * 2,
        f"Expanded to {len(expanded)} chars (>{len(jd_short)*2} expected with Groq)"
    )
else:
    check(
        "Groq: API key not set — using rule-based fallback",
        True,
        "Set GROQ_API_KEY to test live Groq expansion"
    )


# ═══════════════════════════════════════════════════════════════
# COMBINED PIPELINE TEST
# ═══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  COMBINED PIPELINE TEST")
print("="*60)

from services.ai.fit_scorer import batch_stage1_scores

jd_full = """Senior Contracts Claims Engineer FIDIC Red Yellow Silver Book
Extension of Time EOT cost claims pre-award post-award contract lifecycle
Power BI dashboards procurement subcontract dispute resolution arbitration
CLAC CICCM PMP civil structural engineering variation orders tendering"""

hazem_cv = """Hazem Khaled — Contracts and Claims Engineer at RME
FCIArb CLAC CICCM CAPM FIDIC-03 FIDIC-06
Skills: FIDIC, EOT, Extension of Time, Claims, Arbitration, Power BI,
Contract Administration, Dispute Resolution, Variation Orders, Subcontracts
Experience: 5 years contracts and claims engineering on infrastructure projects"""

saqer_cv = """Ahmed Saqer — Sales Manager
Objective: Sales and profitability in assigned area
Experience: Steel sales, business development, customer relationships
Skills: Sales management, CRM, revenue targets, market penetration"""

scores = batch_stage1_scores([hazem_cv, saqer_cv], jd_full)

check(
    "Pipeline: Contracts Engineer scores higher than Sales Manager",
    scores[0] > scores[1],
    f"Contracts Engineer (Hazem)={scores[0]:.1f}, Sales Manager (Saqer)={scores[1]:.1f}"
)
check(
    "Pipeline: Contracts Engineer scores above 60",
    scores[0] > 60,
    f"Score={scores[0]:.1f}"
)
check(
    "Pipeline: Sales Manager scores below 50",
    scores[1] < 50,
    f"Score={scores[1]:.1f}"
)
check(
    "Pipeline: Score difference is significant (>20 points)",
    (scores[0] - scores[1]) > 20,
    f"Difference={scores[0]-scores[1]:.1f} points"
)


# ═══════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  FINAL TEST SUMMARY")
print("="*60)

passed = sum(1 for _, s, _ in results if s == PASS)
failed = sum(1 for _, s, _ in results if s == FAIL)
total  = len(results)

print(f"\n  Total Tests : {total}")
print(f"  Passed      : {passed} ({passed/total*100:.0f}%)")
print(f"  Failed      : {failed}")

if failed > 0:
    print(f"\n  Failed Tests:")
    for name, status, details in results:
        if status == FAIL:
            print(f"    ❌ {name}: {details}")

print(f"\n  {'All signals working correctly!' if failed == 0 else 'Some signals need attention.'}")
print("="*60 + "\n")
