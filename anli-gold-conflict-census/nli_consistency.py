# nli_consistency.py -- census of duplicate (premise, hypothesis) pairs that carry
# CONFLICTING gold labels within a single NLI release.
#
# A "defect" here: the exact same premise+hypothesis pair (or the same pair after a
# defined whitespace/case normalization) appears more than once in the release with
# two or more DIFFERENT gold labels -- so a model cannot satisfy both without error,
# and the pair is ill-defined ground truth. Mirrors the SNLI and MultiNLI censuses.
#
# Authored by AI agents working in MV2's name (Munim, Inc.). Apache-2.0.
# The ANLI corpus keeps its own licence (Nie et al. 2020, facebookresearch/anli).


def normalize(text):
    """Collapse all runs of whitespace to a single space and lowercase. This is the
    ONLY near-duplicate rule applied (no punctuation stripping, no stemming)."""
    return " ".join(text.split()).lower()


def analyze(rows, premise_key, hypothesis_key, label_key,
            skip_labels=("-",), max_examples=50):
    """Census over a list of NLI rows.

    A row is valid iff premise and hypothesis are strings and the label is a
    non-empty string not in skip_labels. Returns counts of distinct pairs and of
    distinct pairs that carry >1 gold label, both exact and normalized.
    """
    valid = 0
    exact = {}   # (premise, hypothesis) -> set of labels
    norm = {}    # (norm_premise, norm_hypothesis) -> {"labels": set, "originals": set}
    for row in rows:
        p = row.get(premise_key)
        h = row.get(hypothesis_key)
        lab = row.get(label_key)
        if not isinstance(p, str) or not isinstance(h, str):
            continue
        if not isinstance(lab, str) or lab in skip_labels or not lab.strip():
            continue
        valid += 1
        exact.setdefault((p, h), set()).add(lab)
        nk = (normalize(p), normalize(h))
        entry = norm.setdefault(nk, {"labels": set(), "originals": set()})
        entry["labels"].add(lab)
        entry["originals"].add((p, h))

    exact_conflict_keys = sorted(k for k, v in exact.items() if len(v) > 1)
    norm_conflict_keys = sorted(k for k, v in norm.items() if len(v["labels"]) > 1)

    exact_examples = [
        {"premise": k[0], "hypothesis": k[1], "labels": sorted(exact[k])}
        for k in exact_conflict_keys[:max_examples]
    ]
    norm_examples = [
        {
            "normalized_premise": k[0],
            "normalized_hypothesis": k[1],
            "labels": sorted(norm[k]["labels"]),
            "originals": [list(o) for o in sorted(norm[k]["originals"])],
        }
        for k in norm_conflict_keys[:max_examples]
    ]

    return {
        "rows_valid": valid,
        "distinct_exact_pairs": len(exact),
        "distinct_norm_pairs": len(norm),
        "exact_conflict_pairs": len(exact_conflict_keys),
        "norm_conflict_pairs": len(norm_conflict_keys),
        "exact_conflict_examples": exact_examples,
        "norm_conflict_examples": norm_examples,
    }


def public_summary(result):
    """Integer-only subset compared against the pre-registered TARGET."""
    return {
        "rows_valid": result["rows_valid"],
        "distinct_exact_pairs": result["distinct_exact_pairs"],
        "distinct_norm_pairs": result["distinct_norm_pairs"],
        "exact_conflict_pairs": result["exact_conflict_pairs"],
        "norm_conflict_pairs": result["norm_conflict_pairs"],
    }
