# backend/services/ai/bm25.py
#
# Pure Python BM25 implementation — no external dependencies.
# BM25 (Best Match 25) is the industry-standard sparse retrieval algorithm.
# It scores documents based on exact term frequency, penalizing common words.
#
# Why BM25 for this use case:
# - Catches exact specialized terms: FIDIC, EOT, CLAC, CICCM, arbitration
# - Heavily penalizes CVs missing required keywords (Ahmed Saqer problem)
# - Complements semantic embeddings which can be fooled by domain-adjacent vocab
#
# Reference: Robertson & Zaragoza (2009). The Probabilistic Relevance Framework:
# BM25 and Beyond. Foundations and Trends in Information Retrieval, 3(4), 333-389.

import math
import re
from typing import List


def _tokenize(text: str) -> List[str]:
    """Lowercase, remove punctuation, split into tokens."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    tokens = text.split()
    # Keep tokens of length 2+ (removes noise like 'a', 'i')
    return [t for t in tokens if len(t) >= 2]


class BM25:
    """
    BM25 scorer for ranking CVs against a job description.

    Parameters:
        k1 (float): Term frequency saturation — controls how much
                    repeated terms boost score. Default 1.5.
        b  (float): Length normalization — penalizes long documents.
                    Default 0.75.
    """

    def __init__(self, corpus: List[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b  = b
        self.corpus_tokens = [_tokenize(doc) for doc in corpus]
        self.n = len(corpus)
        self.avgdl = sum(len(t) for t in self.corpus_tokens) / max(self.n, 1)

        # Build inverted index: term → document frequency
        self.df: dict = {}
        for tokens in self.corpus_tokens:
            for term in set(tokens):
                self.df[term] = self.df.get(term, 0) + 1

    def score(self, query: str, doc_index: int) -> float:
        """Score a single document against a query."""
        query_tokens = _tokenize(query)
        doc_tokens   = self.corpus_tokens[doc_index]
        doc_len      = len(doc_tokens)

        # Term frequency in document
        tf_map: dict = {}
        for token in doc_tokens:
            tf_map[token] = tf_map.get(token, 0) + 1

        score = 0.0
        for term in query_tokens:
            if term not in self.df:
                continue
            tf  = tf_map.get(term, 0)
            df  = self.df[term]
            idf = math.log((self.n - df + 0.5) / (df + 0.5) + 1)
            tf_norm = (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl))
            score += idf * tf_norm

        return float(score)

    def get_all_scores(self, query: str) -> List[float]:
        """
        Score all documents against the query.
        Uses softer normalization to prevent one outlier from
        compressing all other scores.
        """
        raw_scores = [self.score(query, i) for i in range(self.n)]

        if not raw_scores or max(raw_scores) <= 0:
            return [0.0] * self.n

        max_score = max(raw_scores)

        # Use 90th percentile as normalization ceiling instead of max
        # This prevents one unusually keyword-dense CV from compressing everyone else
        sorted_scores = sorted(raw_scores, reverse=True)
        percentile_90_idx = max(0, int(len(sorted_scores) * 0.10))
        ceiling = sorted_scores[percentile_90_idx] if len(sorted_scores) > 1 else max_score
        ceiling = max(ceiling, max_score * 0.5)  # never below 50% of max

        return [round(min(100.0, (s / ceiling) * 100), 2) for s in raw_scores]
