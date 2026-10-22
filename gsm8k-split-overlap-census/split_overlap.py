# split_overlap.py -- census of questions shared by GSM8K's own train and test splits.
#
# Question: does a question string appear in BOTH GSM8K's official train.jsonl and
# test.jsonl (exact match, and after a defined normalization), and when it does, do
# the two splits' final answers (the value after the last "####") agree?
#
# Authored by AI agents working in MV2's name (Munim, Inc.). Apache-2.0.
# GSM8K keeps its own licence (GSM8K, Cobbe et al. 2021).

import re


def normalize(text):
    """Collapse all runs of whitespace to a single space and lowercase.

    This is the ONLY near-duplicate rule applied; nothing else (no punctuation
    stripping, no stemming). Two questions are 'normalized duplicates' iff this
    function returns the same string for both.
    """
    return " ".join(text.split()).lower()


def final_answer(answer_text):
    """Return the GSM8K final answer: text after the LAST '####', stripped, with
    thousands commas and a leading '$' removed. Returns None if there is no '####'.
    """
    if not isinstance(answer_text, str) or "####" not in answer_text:
        return None
    tail = answer_text.rsplit("####", 1)[1].strip()
    tail = tail.replace(",", "").replace("$", "")
    return tail.strip()


def _index(rows):
    """Index one split.

    Returns (valid_count, exact_map, norm_map) where
      exact_map: question_string -> set of final answers seen for it
      norm_map:  normalized_string -> {"answers": set, "originals": set}
    A row counts as valid iff it has a non-empty question string AND a final answer.
    """
    valid = 0
    exact = {}
    norm = {}
    for row in rows:
        q = row.get("question")
        a = row.get("answer", "")
        if not isinstance(q, str) or not q.strip():
            continue
        fa = final_answer(a)
        if fa is None:
            continue
        valid += 1
        exact.setdefault(q, set()).add(fa)
        nk = normalize(q)
        entry = norm.setdefault(nk, {"answers": set(), "originals": set()})
        entry["answers"].add(fa)
        entry["originals"].add(q)
    return valid, exact, norm


def analyze(train_rows, test_rows, max_examples=50):
    """Compute the overlap census between two lists of GSM8K rows
    ({"question": str, "answer": str})."""
    tr_valid, tr_exact, tr_norm = _index(train_rows)
    te_valid, te_exact, te_norm = _index(test_rows)

    exact_keys = sorted(set(tr_exact) & set(te_exact))
    exact_conflicts = 0
    exact_examples = []
    for q in exact_keys:
        conflict = len(tr_exact[q] | te_exact[q]) > 1
        if conflict:
            exact_conflicts += 1
        if len(exact_examples) < max_examples:
            exact_examples.append({
                "question": q,
                "train_answers": sorted(tr_exact[q]),
                "test_answers": sorted(te_exact[q]),
                "conflict": conflict,
            })

    norm_keys = sorted(set(tr_norm) & set(te_norm))
    norm_conflicts = 0
    norm_examples = []
    for k in norm_keys:
        conflict = len(tr_norm[k]["answers"] | te_norm[k]["answers"]) > 1
        if conflict:
            norm_conflicts += 1
        if len(norm_examples) < max_examples:
            norm_examples.append({
                "normalized": k,
                "train_originals": sorted(tr_norm[k]["originals"]),
                "test_originals": sorted(te_norm[k]["originals"]),
                "train_answers": sorted(tr_norm[k]["answers"]),
                "test_answers": sorted(te_norm[k]["answers"]),
                "conflict": conflict,
            })

    return {
        "train_rows_valid": tr_valid,
        "test_rows_valid": te_valid,
        "train_distinct_exact": len(tr_exact),
        "test_distinct_exact": len(te_exact),
        "exact_overlap_pairs": len(exact_keys),
        "exact_overlap_answer_conflicts": exact_conflicts,
        "norm_overlap_pairs": len(norm_keys),
        "norm_overlap_answer_conflicts": norm_conflicts,
        "exact_overlap_examples": exact_examples,
        "norm_overlap_examples": norm_examples,
    }


def public_summary(result):
    """The integer-only subset compared against the pre-registered TARGET."""
    return {
        "train_rows_valid": result["train_rows_valid"],
        "test_rows_valid": result["test_rows_valid"],
        "train_distinct_exact": result["train_distinct_exact"],
        "test_distinct_exact": result["test_distinct_exact"],
        "exact_overlap_pairs": result["exact_overlap_pairs"],
        "exact_overlap_answer_conflicts": result["exact_overlap_answer_conflicts"],
        "norm_overlap_pairs": result["norm_overlap_pairs"],
        "norm_overlap_answer_conflicts": result["norm_overlap_answer_conflicts"],
    }
