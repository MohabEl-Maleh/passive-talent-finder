"""
evaluate_pool_test.py
─────────────────────────────────────────────────────────────────────────────
Realistic evaluation of the Passive Talent Finder hybrid scoring pipeline.

How it works:
  For each test run:
    1. Pick a Job Description that has known selected candidates
    2. Take those selected candidates as the "true positives"
    3. Mix them with random candidates from OTHER roles (noise/negatives)
    4. Run the hybrid scorer on the full pool
    5. Check: do the true positives rank at the TOP?

This simulates a real recruiter scenario — a pool of mixed CVs, one JD,
and the system must surface the right people.

Usage:
    python evaluate_pool_test.py --csv ml/data/preprocessed_ats_dataset.csv
    python evaluate_pool_test.py --csv ml/data/preprocessed_ats_dataset.csv --role "Software Engineer"
    python evaluate_pool_test.py --csv ml/data/preprocessed_ats_dataset.csv --pool_size 50 --top_k 10
    python evaluate_pool_test.py --csv ml/data/preprocessed_ats_dataset.csv --no_semantic

Place this file inside:  passive-talent-finder/ml/scripts/
─────────────────────────────────────────────────────────────────────────────
"""

import argparse
import math
import sys
import random
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

# ── Sentence Transformer ─────────────────────────────────────────────────
try:
    from sentence_transformers import SentenceTransformer, util
    SEMANTIC_AVAILABLE = True
except ImportError:
    print("[WARN] sentence-transformers not installed — semantic signal skipped.")
    SEMANTIC_AVAILABLE = False

# ── BM25 ─────────────────────────────────────────────────────────────────
try:
    from rank_bm25 import BM25Okapi
    BM25_LIB = "rank_bm25"
except ImportError:
    BM25_LIB = None


# ─────────────────────────────────────────────────────────────────────────
#  Pure Python BM25 (mirrors your bm25.py)
# ─────────────────────────────────────────────────────────────────────────
class BM25Pure:
    def __init__(self, corpus, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self._corpus = corpus
        self.N = len(corpus)
        self.avgdl = sum(len(d) for d in corpus) / max(self.N, 1)
        self.df = {}
        self.idf = {}
        for doc in corpus:
            for term in set(doc):
                self.df[term] = self.df.get(term, 0) + 1
        for term, freq in self.df.items():
            self.idf[term] = math.log((self.N - freq + 0.5) / (freq + 0.5) + 1)

    def get_scores(self, query_tokens):
        scores = []
        for doc in self._corpus:
            tf = {}
            for t in doc:
                tf[t] = tf.get(t, 0) + 1
            dl = len(doc)
            s = 0.0
            for t in query_tokens:
                if t not in tf:
                    continue
                idf = self.idf.get(t, 0)
                f = tf[t]
                s += idf * (f * (self.k1 + 1)) / (
                    f + self.k1 * (1 - self.b + self.b * dl / max(self.avgdl, 1))
                )
            scores.append(s)
        return scores


# ─────────────────────────────────────────────────────────────────────────
#  Scoring helpers
# ─────────────────────────────────────────────────────────────────────────
def tokenize(text: str):
    import re
    return re.findall(r'\b\w+\b', text.lower())


def keyword_score(jd_text: str, cv_text: str) -> float:
    import re
    jd_words = set(re.findall(r'\b\w{4,}\b', jd_text.lower()))
    cv_words  = set(re.findall(r'\b\w{4,}\b', cv_text.lower()))
    if not jd_words:
        return 0.0
    matched = jd_words & cv_words
    partial = sum(
        0.5 for w in jd_words
        if any(w in cw or cw in w for cw in cv_words) and w not in matched
    )
    return min((len(matched) + partial) / len(jd_words), 1.0)


def skill_overlap_score(jd_text: str, cv_text: str) -> float:
    import re
    skill_pattern = r'\b[A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?\b'
    jd_skills = set(re.findall(skill_pattern, jd_text))
    cv_skills  = set(re.findall(skill_pattern, cv_text))
    if not jd_skills:
        return 0.0
    return len(jd_skills & cv_skills) / len(jd_skills)


# ─────────────────────────────────────────────────────────────────────────
#  Hybrid scorer — same formula as fit_scorer.py
# ─────────────────────────────────────────────────────────────────────────
def score_candidates(jd_text: str, resumes: list, model=None) -> np.ndarray:
    n = len(resumes)

    # Signal 1: Semantic (40%)
    if SEMANTIC_AVAILABLE and model is not None:
        jd_vec  = model.encode(jd_text, convert_to_tensor=True)
        cv_vecs = model.encode(resumes, convert_to_tensor=True,
                               batch_size=64, show_progress_bar=False)
        sem_scores = util.cos_sim(jd_vec, cv_vecs)[0].cpu().numpy()
        sem_scores = np.clip(sem_scores, 0, 1)
    else:
        sem_scores = np.zeros(n)

    # Signal 2: Keyword Match (25%)
    kw_scores = np.array([keyword_score(jd_text, r) for r in resumes])

    # Signal 3: BM25 (20%)
    corpus_tokens = [tokenize(r) for r in resumes]
    query_tokens  = tokenize(jd_text)
    if BM25_LIB == "rank_bm25":
        bm25     = BM25Okapi(corpus_tokens)
        raw_bm25 = np.array(bm25.get_scores(query_tokens), dtype=float)
    else:
        bm25     = BM25Pure(corpus_tokens)
        raw_bm25 = np.array(bm25.get_scores(query_tokens), dtype=float)
    max_bm25    = raw_bm25.max()
    bm25_scores = raw_bm25 / max_bm25 if max_bm25 > 0 else raw_bm25

    # Signal 4: Skill Overlap (15%)
    sk_scores = np.array([skill_overlap_score(jd_text, r) for r in resumes])

    # Combine
    return 0.40 * sem_scores + 0.25 * kw_scores + 0.20 * bm25_scores + 0.15 * sk_scores


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
    dcg  = sum(ranked_labels[i] / math.log2(i + 2)
               for i in range(min(k, len(ranked_labels))))
    ideal = sorted(ranked_labels, reverse=True)
    idcg = sum(ideal[i] / math.log2(i + 2)
               for i in range(min(k, len(ideal))))
    return dcg / idcg if idcg > 0 else 0.0

def mrr(ranked_labels):
    for i, label in enumerate(ranked_labels):
        if label == 1:
            return 1.0 / (i + 1)
    return 0.0

def baseline_random_metrics(labels, k, n_trials=300):
    labels = list(labels)
    p_vals, r_vals, n_vals, m_vals = [], [], [], []
    for _ in range(n_trials):
        shuffled = labels.copy()
        random.shuffle(shuffled)
        p_vals.append(precision_at_k(shuffled, k))
        r_vals.append(recall_at_k(shuffled, k, sum(labels)))
        n_vals.append(ndcg_at_k(shuffled, k))
        m_vals.append(mrr(shuffled))
    return np.mean(p_vals), np.mean(r_vals), np.mean(n_vals), np.mean(m_vals)


# ─────────────────────────────────────────────────────────────────────────
#  Build one test pool
# ─────────────────────────────────────────────────────────────────────────
def build_pool(jd_text, role_norm, positives_df, all_df, pool_size, seed):
    """
    positives_df : rows that match this JD (decision=select)
    all_df       : full dataset to sample negatives from
    Returns a DataFrame with columns: Name, Resume, label (1/0)
    """
    rng = random.Random(seed)

    # Positives — all selected candidates for this JD
    pos = positives_df[['Name', 'Resume']].copy()
    pos['label'] = 1

    # Negatives — random candidates from OTHER roles
    other_roles = all_df[all_df['Role_norm'] != role_norm]
    n_neg = max(pool_size - len(pos), len(pos))  # at least as many negatives as positives
    n_neg = min(n_neg, len(other_roles))

    neg_idx = rng.sample(range(len(other_roles)), n_neg)
    neg = other_roles.iloc[neg_idx][['Name', 'Resume']].copy()
    neg['label'] = 0

    pool = pd.concat([pos, neg], ignore_index=True)
    pool = pool.sample(frac=1, random_state=seed).reset_index(drop=True)  # shuffle
    return pool


# ─────────────────────────────────────────────────────────────────────────
#  Run one pool test
# ─────────────────────────────────────────────────────────────────────────
def run_pool_test(jd_text, role, pool, model, top_k, verbose=False):
    resumes = pool['Resume'].tolist()
    labels  = pool['label'].tolist()
    names   = pool['Name'].tolist()
    n_pos   = sum(labels)

    fit_scores    = score_candidates(jd_text, resumes, model)
    ranked_idx    = np.argsort(fit_scores)[::-1]
    ranked_labels = [labels[i] for i in ranked_idx]
    ranked_names  = [names[i] for i in ranked_idx]
    ranked_scores = fit_scores[ranked_idx]

    k  = min(top_k, len(labels))
    p  = precision_at_k(ranked_labels, k)
    r  = recall_at_k(ranked_labels, k, n_pos)
    nd = ndcg_at_k(ranked_labels, k)
    mr = mrr(ranked_labels)
    bp, br, bn, bm = baseline_random_metrics(labels, k)

    if verbose:
        print(f"\n  Pool size: {len(pool)} | True matches: {n_pos} | Showing top {k}")
        print(f"  JD: {jd_text[:120].strip()}...")
        print(f"\n  {'Rank':<5} {'Name':<25} {'Score':>7}  {'Match'}")
        print(f"  {'-'*55}")
        for rank, (name, score, label) in enumerate(
            zip(ranked_names[:k], ranked_scores[:k], ranked_labels[:k]), 1
        ):
            flag = "✅ MATCH" if label == 1 else "❌ no match"
            bar  = "█" * int(score * 25)
            print(f"  #{rank:<4} {name:<25} {score*100:>6.1f}%  {flag}  {bar}")

        print(f"\n  {'Metric':<20} {'Our System':>12} {'Baseline (random)':>18} {'Δ':>6}")
        print(f"  {'-'*60}")
        for lbl, our, bas in [
            (f"Precision@{k}", p,  bp),
            (f"Recall@{k}",    r,  br),
            (f"NDCG@{k}",      nd, bn),
            ("MRR",            mr, bm),
        ]:
            imp   = our - bas
            scale = 1 if lbl == "MRR" else 100
            unit  = "" if lbl == "MRR" else "%"
            sign  = "+" if imp >= 0 else ""
            print(f"  {lbl:<20} {our*scale:>11.1f}{unit}  {bas*scale:>17.1f}{unit}  {sign}{imp*scale:.1f}{unit}")

    return {"role": role, "pool_size": len(pool), "n_positives": n_pos,
            "precision": p, "recall": r, "ndcg": nd, "mrr": mr,
            "baseline_precision": bp, "baseline_recall": br,
            "baseline_ndcg": bn, "baseline_mrr": bm}


# ─────────────────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Pool-based evaluation of Passive Talent Finder")
    parser.add_argument("--csv",         required=True,
                        help="Path to preprocessed_ats_dataset.csv")
    parser.add_argument("--role",        default=None,
                        help="Test a single role (e.g. 'Software Engineer')")
    parser.add_argument("--pool_size",   type=int, default=50,
                        help="Total candidates per pool (default: 50)")
    parser.add_argument("--top_k",       type=int, default=10,
                        help="K for Precision@K / NDCG@K (default: 10)")
    parser.add_argument("--min_positives", type=int, default=3,
                        help="Min selected candidates needed per JD (default: 3)")
    parser.add_argument("--no_semantic", action="store_true",
                        help="Skip semantic signal (faster)")
    parser.add_argument("--seed",        type=int, default=42,
                        help="Random seed (default: 42)")
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    # Load + normalize
    df = pd.read_csv(args.csv)
    df['Role_norm'] = df['Role'].str.strip().str.lower()
    df['decision']  = df['decision'].str.strip().str.lower()
    print(f"\n[INFO] Loaded {len(df)} rows | {df['Role_norm'].nunique()} unique roles")

    # Load model
    model = None
    if SEMANTIC_AVAILABLE and not args.no_semantic:
        print("[INFO] Loading all-mpnet-base-v2...")
        model = SentenceTransformer("all-mpnet-base-v2")
        print("[INFO] Model loaded ✓")
    else:
        print("[INFO] Running WITHOUT semantic signal")

    all_results = []
    roles_to_test = ([args.role.strip().lower()] if args.role
                     else sorted(df['Role_norm'].unique().tolist()))

    for role_norm in roles_to_test:
        role_df = df[df['Role_norm'] == role_norm]

        # Find JDs with enough selected candidates
        valid_jds = (role_df[role_df['decision'] == 'select']
                     .groupby('Job_Description')
                     .filter(lambda x: len(x) >= args.min_positives)
                     ['Job_Description'].unique())

        if len(valid_jds) == 0:
            print(f"\n[SKIP] {role_norm} — no JD with {args.min_positives}+ selected candidates")
            continue

        # Pick the JD with the most selected candidates for this role
        best_jd = max(valid_jds,
                      key=lambda jd: (role_df[(role_df['Job_Description'] == jd) &
                                              (role_df['decision'] == 'select')].shape[0]))

        positives_df = role_df[(role_df['Job_Description'] == best_jd) &
                               (role_df['decision'] == 'select')]

        print(f"\n{'='*70}")
        print(f"  Role    : {role_norm}")
        print(f"  True matches in pool : {len(positives_df)}")
        print(f"  Pool size            : {args.pool_size} (rest are random non-matching CVs)")
        print(f"{'='*70}")

        pool = build_pool(best_jd, role_norm, positives_df, df,
                          args.pool_size, args.seed)

        result = run_pool_test(best_jd, role_norm, pool, model,
                               args.top_k, verbose=True)
        all_results.append(result)

    # ── Final aggregate ───────────────────────────────────────────────────
    if len(all_results) > 1:
        res_df = pd.DataFrame(all_results)
        print(f"\n\n{'='*70}")
        print(f"  FINAL AGGREGATE — {len(all_results)} ROLES  (pool={args.pool_size}, K={args.top_k})")
        print(f"{'='*70}")
        print(f"\n  {'Metric':<20} {'Our System':>12} {'Baseline':>12} {'Improvement':>12}")
        print(f"  {'-'*58}")
        for lbl, m, b in [
            (f"Precision@{args.top_k}", "precision", "baseline_precision"),
            (f"Recall@{args.top_k}",    "recall",    "baseline_recall"),
            (f"NDCG@{args.top_k}",      "ndcg",      "baseline_ndcg"),
            ("MRR",                      "mrr",        "baseline_mrr"),
        ]:
            our = res_df[m].mean(); bas = res_df[b].mean(); imp = our - bas
            scale = 1 if lbl == "MRR" else 100
            unit  = "" if lbl == "MRR" else "%"
            print(f"  {lbl:<20} {our*scale:>11.1f}{unit}  {bas*scale:>11.1f}{unit}  +{imp*scale:>10.1f}{unit}")

        out_path = "pool_eval_results.csv"
        res_df.to_csv(out_path, index=False)
        print(f"\n  [SAVED] Per-role results → {out_path}")

    print("\n[DONE]\n")


if __name__ == "__main__":
    main()
