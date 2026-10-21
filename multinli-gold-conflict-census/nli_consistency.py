# SPDX-License-Identifier: Apache-2.0
# Part of MV2's eval-reliability audits (Munim, Inc.). Made with AI.
"""Census of conflicting gold labels on duplicate NLI pairs.

MultiNLI, like SNLI, pairs each premise with multiple written hypotheses, so a
premise recurring with different labels is expected, not a defect. This census
instead asks a self-consistency question the design does NOT license: within one
released split, does the SAME (premise, hypothesis) pair ever carry two
different gold labels? Such a pair cannot be right both times.

Two keys are used: the exact (premise, hypothesis) string pair, and a normalized
pair (lowercased, whitespace-collapsed, trailing period dropped). No-consensus
rows (gold_label '-') are excluded, since they carry no gold label to conflict.
"""

import re
from collections import Counter, defaultdict

VALID = {"entailment", "neutral", "contradiction"}


def normalize(s):
    """Deterministic surface normalization for near-duplicate matching."""
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = s.rstrip(".")
    s = s.strip()
    return s


def analyze(rows):
    """Census an iterable of (premise, hypothesis, gold_label) triples.

    Returns counts plus the conflicting-pair maps (private keys, for examples).
    """
    exact = defaultdict(lambda: [set(), 0])   # (p, h) -> [labels, occurrences]
    norm = defaultdict(set)                    # (np, nh) -> labels
    n_valid = 0

    for premise, hypothesis, gold in rows:
        if gold not in VALID:
            continue  # skip '-' (no majority); nothing to conflict
        n_valid += 1
        slot = exact[(premise, hypothesis)]
        slot[0].add(gold)
        slot[1] += 1
        norm[(normalize(premise), normalize(hypothesis))].add(gold)

    exact_conflicts = {k: sorted(v[0]) for k, v in exact.items() if len(v[0]) > 1}
    norm_conflicts = {k: sorted(v) for k, v in norm.items() if len(v) > 1}
    duplicate_exact = {k: v[1] for k, v in exact.items() if v[1] > 1}

    return {
        "rows_valid": n_valid,
        "distinct_exact_pairs": len(exact),
        "exact_conflict_pairs": len(exact_conflicts),
        "duplicate_exact_pairs": len(duplicate_exact),
        "distinct_norm_pairs": len(norm),
        "norm_conflict_pairs": len(norm_conflicts),
        "_exact_conflicts": exact_conflicts,
        "_norm_conflicts": norm_conflicts,
    }
