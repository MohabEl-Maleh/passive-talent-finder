"""
evaluate_kaggle_dataset.py
─────────────────────────────────────────────────────────────────────────────
Evaluates the Passive Talent Finder hybrid scoring pipeline against the
Kaggle job_applicant_dataset.csv using Precision@K, Recall@K, NDCG@K, MRR.

Usage:
    python evaluate_kaggle_dataset.py --csv path/to/job_applicant_dataset.csv
    python evaluate_kaggle_dataset.py --csv path/to/job_applicant_dataset.csv --job_role "Software Engineer"
    python evaluate_kaggle_dataset.py --csv path/to/job_applicant_dataset.csv --top_k 20

Place this file inside:  passive-talent-finder/ml/scripts/
─────────────────────────────────────────────────────────────────────────────
"""

import argparse
import math
import sys
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

# ── Sentence Transformer ──────────────────────────────────────────────────
try:
    from sentence_transformers import SentenceTransformer, util
    SEMANTIC_AVAILABLE = True
except ImportError:
    print("[WARN] sentence-transformers not installed — semantic signal will be skipped.")
    SEMANTIC_AVAILABLE = False

# ── BM25 ──────────────────────────────────────────────────────────────────
try:
    from rank_bm25 import BM25Okapi
    BM25_LIB = "rank_bm25"
except ImportError:
    BM25_LIB = None

# ─────────────────────────────────────────────────────────────────────────
#  BM25 implementation (pure Python fallback — mirrors your bm25.py)
# ─────────────────────────────────────────────────────────────────────────
class BM25Pure:
    def __init__(self, corpus, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.N = len(corpus)
        self.avgdl = sum(len(d) for d in corpus) / max(self.N, 1)
        self.df = {}
        self.idf = {}
        for doc in corpus:
            for term in set(doc):
                self.df[term] = self.df.get(term, 0) + 1
        for term, freq in self.df.items():
            self.idf[term] = math.log((self.N - freq + 0.5) / (freq + 0.5) + 1)

    def score(self, query_tokens, doc_tokens):
        tf = {}
        for t in doc_tokens:
            tf[t] = tf.get(t, 0) + 1
        dl = len(doc_tokens)
        score = 0.0
        for t in query_tokens:
            if t not in tf:
                continue
            idf = self.idf.get(t, 0)
            f = tf[t]
            score += idf * (f * (self.k1 + 1)) / (f + self.k1 * (1 - self.b + self.b * dl / max(self.avgdl, 1)))
        return score

    def get_scores(self, query_tokens):
        return [self.score(query_tokens, doc) for doc in self.corpus]


# ─────────────────────────────────────────────────────────────────────────
#  Scoring helpers
# ─────────────────────────────────────────────────────────────────────────
def tokenize(text: str):
    import re
    return re.findall(r'\b\w+\b', text.lower())


def keyword_score(jd_text: str, cv_text: str) -> float:
    """Signal 2 — keyword match (mirrors keyword_match in fit_scorer.py)."""
    import re
    jd_words = set(re.findall(r'\b\w{4,}\b', jd_text.lower()))
    cv_words  = set(re.findall(r'\b\w{4,}\b', cv_text.lower()))
    if not jd_words:
        return 0.0
    matched = jd_words & cv_words
    partial = sum(0.5 for w in jd_words if any(w in cw or cw in w for cw in cv_words) and w not in matched)
    return min((len(matched) + partial) / len(jd_words), 1.0)


def skill_overlap_score(jd_text: str, cv_text: str) -> float:
    """Signal 4 — simple skill overlap (no Groq synonyms in offline eval)."""
    import re
    # Extract capitalised or comma-separated skill-like tokens
    skill_pattern = r'\b[A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?\b'
    jd_skills = set(re.findall(skill_pattern, jd_text))
    cv_skills  = set(re.findall(skill_pattern, cv_text))
    if not jd_skills:
        return 0.0
    return len(jd_skills & cv_skills) / len(jd_skills)


# ─────────────────────────────────────────────────────────────────────────
#  Main hybrid scorer
# ─────────────────────────────────────────────────────────────────────────
def score_candidates(jd_text: str, resumes: list[str], model=None) -> np.ndarray:
    """
    Returns an array of fit_scores aligned with `resumes`.
    Formula: 0.40*semantic + 0.25*keyword + 0.20*BM25 + 0.15*skill_overlap
    """
    n = len(resumes)

    # ── Signal 1: Semantic (40%) ──────────────────────────────────────────
    if SEMANTIC_AVAILABLE and model is not None:
        jd_vec  = model.encode(jd_text,  convert_to_tensor=True)
        cv_vecs = model.encode(resumes,  convert_to_tensor=True, batch_size=64, show_progress_bar=False)
        sem_scores = util.cos_sim(jd_vec, cv_vecs)[0].cpu().numpy()
        sem_scores = np.clip(sem_scores, 0, 1)
    else:
        sem_scores = np.zeros(n)

    # ── Signal 2: Keyword Match (25%) ─────────────────────────────────────
    kw_scores = np.array([keyword_score(jd_text, r) for r in resumes])

    # ── Signal 3: BM25 (20%) ──────────────────────────────────────────────
    corpus_tokens = [tokenize(r) for r in resumes]
    query_tokens  = tokenize(jd_text)

    if BM25_LIB == "rank_bm25":
        bm25 = BM25Okapi(corpus_tokens)
        raw_bm25 = np.array(bm25.get_scores(query_tokens), dtype=float)
    else:
        bm25 = BM25Pure(corpus_tokens)
        raw_bm25 = np.array(bm25.get_scores(query_tokens), dtype=float)

    max_bm25 = raw_bm25.max()
    bm25_scores = raw_bm25 / max_bm25 if max_bm25 > 0 else raw_bm25

    # ── Signal 4: Skill Overlap (15%) ────────────────────────────────────
    sk_scores = np.array([skill_overlap_score(jd_text, r) for r in resumes])

    # ── Combine ───────────────────────────────────────────────────────────
    fit = 0.40 * sem_scores + 0.25 * kw_scores + 0.20 * bm25_scores + 0.15 * sk_scores
    return fit


# ─────────────────────────────────────────────────────────────────────────
#  IR Metrics
# ─────────────────────────────────────────────────────────────────────────
def precision_at_k(ranked_labels, k):
    return sum(ranked_labels[:k]) / k

def recall_at_k(ranked_labels, k, total_positives):
    if total_positives == 0:
        return 0.0
    return sum(ranked_labels[:k]) / total_positives

def ndcg_at_k(ranked_labels, k):
    dcg  = sum(ranked_labels[i] / math.log2(i + 2) for i in range(min(k, len(ranked_labels))))
    ideal = sorted(ranked_labels, reverse=True)
    idcg = sum(ideal[i] / math.log2(i + 2) for i in range(min(k, len(ideal))))
    return dcg / idcg if idcg > 0 else 0.0

def mrr(ranked_labels):
    for i, label in enumerate(ranked_labels):
        if label == 1:
            return 1.0 / (i + 1)
    return 0.0

def baseline_random_metrics(labels, k, n_trials=500):
    """Simulate random ranking as baseline."""
    labels = list(labels)
    p_vals, r_vals, n_vals, m_vals = [], [], [], []
    for _ in range(n_trials):
        shuffled = labels.copy()
        np.random.shuffle(shuffled)
        p_vals.append(precision_at_k(shuffled, k))
        r_vals.append(recall_at_k(shuffled, k, sum(labels)))
        n_vals.append(ndcg_at_k(shuffled, k))
        m_vals.append(mrr(shuffled))
    return np.mean(p_vals), np.mean(r_vals), np.mean(n_vals), np.mean(m_vals)


# ─────────────────────────────────────────────────────────────────────────
#  Evaluate one job role
# ─────────────────────────────────────────────────────────────────────────
def evaluate_job(job_role: str, subset: pd.DataFrame, model, top_k: int):
    jd_text = subset['Job Description'].iloc[0]
    resumes = subset['Resume'].tolist()
    labels  = subset['Best Match'].tolist()
    n_pos   = sum(labels)

    print(f"\n{'='*70}")
    print(f"  Job Role : {job_role}")
    print(f"  Candidates: {len(resumes)} | Positives: {n_pos}")
    print(f"  JD snippet: {jd_text[:120].strip()}...")
    print(f"{'='*70}")

    # Score
    fit_scores = score_candidates(jd_text, resumes, model)

    # Rank
    ranked_idx = np.argsort(fit_scores)[::-1]
    ranked_labels = [labels[i] for i in ranked_idx]
    ranked_names  = subset['Job Applicant Name'].iloc[ranked_idx].tolist()
    ranked_roles  = subset['Job Roles'].iloc[ranked_idx].tolist()
    ranked_scores = fit_scores[ranked_idx]

    # Metrics
    p  = precision_at_k(ranked_labels, top_k)
    r  = recall_at_k(ranked_labels, top_k, n_pos)
    nd = ndcg_at_k(ranked_labels, top_k)
    mr = mrr(ranked_labels)

    # Baseline
    bp, br, bn, bm = baseline_random_metrics(labels, top_k)

    # Print top K
    print(f"\n  {'Rank':<5} {'Name':<25} {'Score':>7}  {'Match':>6}")
    print(f"  {'-'*50}")
    for rank, (name, score, label) in enumerate(zip(ranked_names[:top_k], ranked_scores[:top_k], ranked_labels[:top_k]), 1):
        flag = "✅" if label == 1 else "❌"
        bar  = "█" * int(score * 20)
        print(f"  #{rank:<4} {name:<25} {score*100:>6.1f}%  {flag}  {bar}")

    print(f"\n  {'Metric':<20} {'Our System':>12} {'Baseline (random)':>18}")
    print(f"  {'-'*52}")
    print(f"  {'Precision@'+str(top_k):<20} {p*100:>11.1f}%  {bp*100:>17.1f}%")
    print(f"  {'Recall@'+str(top_k):<20} {r*100:>11.1f}%  {br*100:>17.1f}%")
    print(f"  {'NDCG@'+str(top_k):<20} {nd*100:>11.1f}%  {bn*100:>17.1f}%")
    print(f"  {'MRR':<20} {mr:>12.3f}  {bm:>17.3f}")

    return {
        "job_role": job_role,
        "n_candidates": len(resumes),
        "n_positives": n_pos,
        "precision": p, "recall": r, "ndcg": nd, "mrr": mr,
        "baseline_precision": bp, "baseline_recall": br,
        "baseline_ndcg": bn, "baseline_mrr": bm,
    }


# ─────────────────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Evaluate Passive Talent Finder on Kaggle dataset")
    parser.add_argument("--csv",      required=True,  help="Path to job_applicant_dataset.csv")
    parser.add_argument("--job_role", default=None,   help="Evaluate a single job role (e.g. 'Software Engineer')")
    parser.add_argument("--top_k",   type=int, default=10, help="K for Precision@K / NDCG@K (default: 10)")
    parser.add_argument("--no_semantic", action="store_true", help="Skip semantic signal (faster, no GPU needed)")
    args = parser.parse_args()

    # Load data
    df = pd.read_csv(args.csv)
    print(f"\n[INFO] Loaded {len(df)} rows | {df['Job Roles'].nunique()} unique job roles")

    # Load model
    model = None
    if SEMANTIC_AVAILABLE and not args.no_semantic:
        print("[INFO] Loading all-mpnet-base-v2 (uses locally cached model)...")
        model = SentenceTransformer("all-mpnet-base-v2")
        print("[INFO] Model loaded ✓")
    else:
        print("[INFO] Running WITHOUT semantic signal (keyword + BM25 + skill_overlap only)")

    results = []

    if args.job_role:
        # Single job role
        subset = df[df['Job Roles'] == args.job_role].reset_index(drop=True)
        if subset.empty:
            print(f"[ERROR] Job role '{args.job_role}' not found.")
            print("Available roles:", df['Job Roles'].unique().tolist())
            sys.exit(1)
        results.append(evaluate_job(args.job_role, subset, model, args.top_k))
    else:
        # All job roles
        for job_role, subset in df.groupby('Job Roles'):
            subset = subset.reset_index(drop=True)
            results.append(evaluate_job(job_role, subset, model, args.top_k))

    # ── Aggregate summary ─────────────────────────────────────────────────
    if len(results) > 1:
        res_df = pd.DataFrame(results)
        print(f"\n\n{'='*70}")
        print(f"  AGGREGATE RESULTS ACROSS {len(results)} JOB ROLES  (K={args.top_k})")
        print(f"{'='*70}")
        metrics = ["precision", "recall", "ndcg", "mrr"]
        base    = ["baseline_precision", "baseline_recall", "baseline_ndcg", "baseline_mrr"]
        labels  = [f"Precision@{args.top_k}", f"Recall@{args.top_k}", f"NDCG@{args.top_k}", "MRR"]
        print(f"\n  {'Metric':<20} {'Our System':>12} {'Baseline':>12} {'Improvement':>12}")
        print(f"  {'-'*58}")
        for m, b, lbl in zip(metrics, base, labels):
            our = res_df[m].mean()
            bas = res_df[b].mean()
            imp = our - bas
            unit = "" if lbl == "MRR" else "%"
            scale = 1 if lbl == "MRR" else 100
            print(f"  {lbl:<20} {our*scale:>11.1f}{unit}  {bas*scale:>11.1f}{unit}  +{imp*scale:>10.1f}{unit}")

        # Save results CSV
        out_path = "kaggle_eval_results.csv"
        res_df.to_csv(out_path, index=False)
        print(f"\n  [SAVED] Detailed results → {out_path}")

    print("\n[DONE]\n")


if __name__ == "__main__":
    main()
